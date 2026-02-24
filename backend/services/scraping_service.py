import asyncio
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import Car, ScrapingSession, DamageKeyword
from scrapers.marktplaats_scraper import MarktplaatsScraper
from scrapers.schadevoertuigen_scraper import SchadevoertuigenScraper
from scrapers.schadeautos_scraper import SchadeautosScraper
from services.notification_service import NotificationService
from decouple import config

class ScrapingService:
    def __init__(self):
        self.scrapers = {
            'marktplaats': MarktplaatsScraper(),
            'schadevoertuigen': SchadevoertuigenScraper(),
            'schadeautos': SchadeautosScraper()
        }
        self.notification_service = NotificationService()
        self.is_running = False
        self.scraping_task = None
        self.logger = logging.getLogger(__name__)

        # Specific search terms for damaged cars (not accessories)
        self.damage_search_terms = [
            'auto met schade', 'beschadigde personenauto', 'cosmetische schade auto',
            'lichte schade personenauto', 'lakschade auto', 'auto deukjes', 'hagelschade auto',
            'auto parkeerdeuk', 'auto krassen', 'personenauto schade'
        ]

    async def start_background_tasks(self):
        if not self.is_running:
            self.is_running = True
            self.scraping_task = asyncio.create_task(self._periodic_scraping())
            self.logger.info("Background scraping tasks started")

    async def stop_background_tasks(self):
        self.is_running = False
        if self.scraping_task:
            self.scraping_task.cancel()
            try:
                await self.scraping_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Background scraping tasks stopped")

    async def _periodic_scraping(self):
        interval_minutes = config("SCRAPING_INTERVAL_MINUTES", default=30, cast=int)

        while self.is_running:
            try:
                await self.run_all_scrapers()
                await asyncio.sleep(interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic scraping: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def run_all_scrapers(self):
        self.logger.info("Starting scraping session for all websites")

        for website_name, scraper in self.scrapers.items():
            try:
                await self.run_single_scraper(website_name, scraper)
            except Exception as e:
                self.logger.error(f"Error scraping {website_name}: {e}")

    async def run_single_scraper(self, website_name: str, scraper):
        db = SessionLocal()
        session = ScrapingSession(website=website_name)

        try:
            db.add(session)
            db.commit()
            db.refresh(session)

            self.logger.info(f"Starting scraper for {website_name}")

            await scraper.setup()
            cars_data = await scraper.scrape_search_results(
                self.damage_search_terms,
                max_pages=5
            )

            cars_added = 0
            cars_updated = 0

            for car_data in cars_data:
                try:
                    result = await self._process_car_data(car_data, db)
                    if result == "added":
                        cars_added += 1
                    elif result == "updated":
                        cars_updated += 1
                except Exception as e:
                    self.logger.error(f"Error processing car data: {e}")
                    session.errors_count += 1

            # Update session results
            session.completed_at = datetime.utcnow()
            session.status = "completed"
            session.cars_found = len(cars_data)
            session.cars_added = cars_added
            session.cars_updated = cars_updated

            db.commit()

            self.logger.info(
                f"Completed {website_name}: {cars_added} added, {cars_updated} updated"
            )

            # Send notifications for new cars
            if cars_added > 0:
                await self.notification_service.send_new_cars_notifications(db)

        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
            session.completed_at = datetime.utcnow()
            db.commit()
            self.logger.error(f"Scraping failed for {website_name}: {e}")

        finally:
            await scraper.close()
            db.close()

    async def _process_car_data(self, car_data: Dict, db: Session) -> str:
        # Check if car already exists
        existing_car = db.query(Car).filter(Car.url == car_data['url']).first()

        if existing_car:
            # Update existing car
            updated = False
            for key, value in car_data.items():
                if hasattr(existing_car, key) and getattr(existing_car, key) != value:
                    setattr(existing_car, key, value)
                    updated = True

            if updated:
                existing_car.last_updated = datetime.utcnow()
                db.commit()
                return "updated"
            return "exists"
        else:
            # Create new car
            car = Car(**car_data)
            db.add(car)
            db.commit()
            return "added"

    async def scrape_specific_website(self, website_name: str) -> Dict:
        if website_name not in self.scrapers:
            raise ValueError(f"Unknown website: {website_name}")

        scraper = self.scrapers[website_name]
        await self.run_single_scraper(website_name, scraper)

        # Return session statistics
        db = SessionLocal()
        try:
            latest_session = db.query(ScrapingSession).filter(
                ScrapingSession.website == website_name
            ).order_by(ScrapingSession.started_at.desc()).first()

            if latest_session:
                return {
                    "website": website_name,
                    "status": latest_session.status,
                    "cars_found": latest_session.cars_found,
                    "cars_added": latest_session.cars_added,
                    "cars_updated": latest_session.cars_updated,
                    "errors": latest_session.errors_count,
                    "started_at": latest_session.started_at,
                    "completed_at": latest_session.completed_at
                }
        finally:
            db.close()

        return {"website": website_name, "status": "unknown"}

    def get_scraping_stats(self) -> Dict:
        db = SessionLocal()
        try:
            # Get recent sessions
            recent_sessions = db.query(ScrapingSession).filter(
                ScrapingSession.started_at >= datetime.utcnow() - timedelta(days=7)
            ).all()

            stats = {
                "total_sessions": len(recent_sessions),
                "successful_sessions": len([s for s in recent_sessions if s.status == "completed"]),
                "failed_sessions": len([s for s in recent_sessions if s.status == "failed"]),
                "cars_added_week": sum(s.cars_added or 0 for s in recent_sessions),
                "cars_updated_week": sum(s.cars_updated or 0 for s in recent_sessions),
                "last_scrape": None
            }

            if recent_sessions:
                latest_session = max(recent_sessions, key=lambda x: x.started_at)
                stats["last_scrape"] = latest_session.started_at

            # Today's stats
            today_sessions = [s for s in recent_sessions
                            if s.started_at.date() == datetime.utcnow().date()]

            stats["cars_added_today"] = sum(s.cars_added or 0 for s in today_sessions)
            stats["cars_updated_today"] = sum(s.cars_updated or 0 for s in today_sessions)

            return stats

        finally:
            db.close()

    async def initialize_damage_keywords(self):
        """Initialize the damage keywords in the database"""
        db = SessionLocal()
        try:
            # Check if keywords already exist
            existing_count = db.query(DamageKeyword).count()
            if existing_count > 0:
                return

            # Define damage keywords with categories
            keywords_data = [
                # Dutch cosmetic damage terms
                ('cosmetische schade', 'nl', 'cosmetic', 1.0),
                ('lichte schade', 'nl', 'cosmetic', 1.0),
                ('lakschade', 'nl', 'cosmetic', 0.9),
                ('deukjes', 'nl', 'cosmetic', 0.8),
                ('krassen', 'nl', 'cosmetic', 0.8),
                ('hagelschade', 'nl', 'cosmetic', 0.9),
                ('parkeerdeuk', 'nl', 'cosmetic', 0.7),
                ('bumperdeuk', 'nl', 'cosmetic', 0.7),

                # English cosmetic damage terms
                ('cosmetic damage', 'en', 'cosmetic', 1.0),
                ('minor damage', 'en', 'cosmetic', 1.0),
                ('paint damage', 'en', 'cosmetic', 0.9),
                ('scratch', 'en', 'cosmetic', 0.8),
                ('dent', 'en', 'cosmetic', 0.8),

                # Severe damage terms (to exclude)
                ('motorschade', 'nl', 'severe', 1.0),
                ('versnellingsbak', 'nl', 'severe', 1.0),
                ('frame schade', 'nl', 'severe', 1.0),
                ('water schade', 'nl', 'severe', 1.0),
                ('brand schade', 'nl', 'severe', 1.0),
                ('total loss', 'en', 'severe', 1.0),
                ('engine damage', 'en', 'severe', 1.0),
                ('flood damage', 'en', 'severe', 1.0),
            ]

            for keyword, language, category, weight in keywords_data:
                db_keyword = DamageKeyword(
                    keyword=keyword,
                    language=language,
                    category=category,
                    weight=weight
                )
                db.add(db_keyword)

            db.commit()
            self.logger.info(f"Initialized {len(keywords_data)} damage keywords")

        finally:
            db.close()