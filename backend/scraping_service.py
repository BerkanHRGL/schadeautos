import asyncio
from sqlalchemy.orm import sessionmaker
from database.database import engine
from database.models import Car, ScrapingSession
from scrapers.marktplaats_scraper import MarktplaatsScraper
from scrapers.schadeautos_scraper import SchadeautosScraper
import logging
from datetime import datetime
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Popular hatchbacks in the Netherlands
TARGET_MODELS = [
    # Budget/small hatchbacks
    'volkswagen polo', 'volkswagen up',
    'opel corsa', 'opel astra',
    'renault clio', 'renault megane',
    'peugeot 208', 'peugeot 107', 'peugeot 108', 'peugeot 308',
    'ford fiesta', 'ford focus',
    'toyota yaris', 'toyota aygo', 'toyota corolla',
    'kia picanto', 'kia ceed',
    'hyundai i10', 'hyundai i20', 'hyundai i30',
    'fiat 500', 'fiat punto',
    'citroen c1', 'citroen c3',
    'seat ibiza', 'seat mii', 'seat leon',
    'skoda fabia', 'skoda citigo', 'skoda octavia',
    'suzuki swift',
    'dacia sandero',
    'mini cooper',
    'honda jazz',
    'mazda 2', 'mazda 3',
]


class ScrapingService:
    def __init__(self):
        self.search_terms = list(TARGET_MODELS)

    def _save_car(self, session, car_data: Dict) -> str:
        """Save a single car to DB immediately. Returns 'added', 'updated', or 'skipped'."""
        year = car_data.get('year')
        if year is not None and year < 2014:
            return 'skipped'

        existing_car = session.query(Car).filter_by(url=car_data.get('url')).first()
        if existing_car:
            for key, value in car_data.items():
                if key != 'first_seen' and hasattr(existing_car, key) and value is not None:
                    setattr(existing_car, key, value)
            existing_car.last_updated = datetime.utcnow()
            session.commit()
            return 'updated'
        else:
            new_car = Car(
                url=car_data.get('url'),
                source_website=car_data.get('source_website'),
                title=car_data.get('title'),
                description=car_data.get('description'),
                price=car_data.get('price'),
                make=car_data.get('make'),
                model=car_data.get('model'),
                year=car_data.get('year'),
                mileage=car_data.get('mileage'),
                location=car_data.get('location', ''),
                images=car_data.get('images', []),
                damage_keywords=car_data.get('damage_keywords', []),
                has_cosmetic_damage_only=car_data.get('has_cosmetic_damage_only', True),
                market_price=car_data.get('market_price'),
                profit_percentage=car_data.get('profit_percentage'),
                deal_rating=car_data.get('deal_rating'),
                first_seen=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                is_active=True
            )
            session.add(new_car)
            session.commit()
            return 'added'

    async def _scrape_with_scraper(self, scraper, website_name: str, search_terms: List[str] = None, max_pages: int = 3, on_progress=None) -> Dict:
        """Run a single scraper and save results to database in real-time"""
        session = SessionLocal()
        cars_added = 0
        cars_updated = 0
        cars_found = 0

        try:
            scraping_session = ScrapingSession(
                started_at=datetime.utcnow(),
                website=website_name,
                status='running'
            )
            session.add(scraping_session)
            session.commit()

            logger.info(f"Starting scraping session for {website_name}...")

            await scraper.setup()

            async def on_car_found(car_data: Dict):
                nonlocal cars_added, cars_updated, cars_found
                try:
                    result = self._save_car(session, car_data)
                    cars_found += 1
                    if result == 'added':
                        cars_added += 1
                        logger.info(f"Saved new car: {car_data.get('title', '')[:50]}")
                    elif result == 'updated':
                        cars_updated += 1
                except Exception as e:
                    logger.error(f"Error saving car: {e}")

            await scraper.scrape_search_results(
                search_terms=search_terms or [],
                max_pages=max_pages,
                on_car_found=on_car_found,
                on_progress=on_progress,
                website_name=website_name,
            )

            scraping_session.completed_at = datetime.utcnow()
            scraping_session.status = 'completed'
            scraping_session.cars_found = cars_found
            scraping_session.cars_added = cars_added
            scraping_session.cars_updated = cars_updated
            session.commit()

            logger.info(f"{website_name}: {cars_added} new cars, {cars_updated} updated cars")

            return {
                'website': website_name,
                'success': True,
                'cars_found': cars_found,
                'cars_added': cars_added,
                'cars_updated': cars_updated,
            }

        except Exception as e:
            logger.error(f"Scraping session failed for {website_name}: {e}")
            if 'scraping_session' in locals():
                scraping_session.status = 'failed'
                scraping_session.error_message = str(e)
                scraping_session.completed_at = datetime.utcnow()
                session.commit()
            session.rollback()
            return {
                'website': website_name,
                'success': False,
                'error': str(e)
            }
        finally:
            await scraper.close()
            session.close()

    async def run_scraping_session(self, on_progress=None) -> Dict:
        """Run scraping across all sources"""
        results = []

        # Scrape marktplaats.nl
        try:
            logger.info("=== Starting Marktplaats scraper ===")
            marktplaats = MarktplaatsScraper()
            result = await self._scrape_with_scraper(
                marktplaats, 'marktplaats.nl',
                search_terms=self.search_terms,
                max_pages=3,
                on_progress=on_progress,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Marktplaats scraper failed: {e}")
            results.append({'website': 'marktplaats.nl', 'success': False, 'error': str(e)})

        # Scrape schadeautos.nl - same TARGET_MODELS list as Marktplaats
        try:
            logger.info("=== Starting SchadeAutos scraper ===")
            schadeautos = SchadeautosScraper()
            result = await self._scrape_with_scraper(
                schadeautos, 'schadeautos.nl',
                search_terms=self.search_terms,
                max_pages=5,
                on_progress=on_progress,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"SchadeAutos scraper failed: {e}")
            results.append({'website': 'schadeautos.nl', 'success': False, 'error': str(e)})

        total_added = sum(r.get('cars_added', 0) for r in results)
        total_updated = sum(r.get('cars_updated', 0) for r in results)
        total_found = sum(r.get('cars_found', 0) for r in results)

        logger.info(f"All scraping complete: {total_found} found, {total_added} added, {total_updated} updated")

        return {
            'success': all(r.get('success', False) for r in results),
            'cars_found': total_found,
            'cars_added': total_added,
            'cars_updated': total_updated,
            'results': results
        }


def run_scraping_sync():
    """Synchronous wrapper to run async scraping (for use from threads)"""
    service = ScrapingService()
    return asyncio.run(service.run_scraping_session())
