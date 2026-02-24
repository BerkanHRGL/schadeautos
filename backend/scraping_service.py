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


class ScrapingService:
    def __init__(self):
        self.search_terms = [
            'schade auto',
            'lakschade',
            'cosmetische schade',
            'hagelschade',
            'parkeerdeuk',
            'beschadigde auto',
            'lichte schade'
        ]

    async def _scrape_with_scraper(self, scraper, website_name: str, search_terms: List[str] = None, max_pages: int = 3) -> Dict:
        """Run a single scraper and save results to database"""
        session = SessionLocal()
        cars_added = 0
        cars_updated = 0

        try:
            # Create scraping session record
            scraping_session = ScrapingSession(
                started_at=datetime.utcnow(),
                website=website_name,
                status='running'
            )
            session.add(scraping_session)
            session.commit()

            logger.info(f"Starting scraping session for {website_name}...")

            # Initialize the scraper (sets up Selenium/aiohttp)
            await scraper.setup()

            # Scrape cars
            scraped_cars = await scraper.scrape_search_results(
                search_terms=search_terms or [],
                max_pages=max_pages
            )

            logger.info(f"Scraped {len(scraped_cars)} cars from {website_name}")

            # Process each scraped car
            for car_data in scraped_cars:
                try:
                    existing_car = session.query(Car).filter_by(url=car_data.get('url')).first()

                    if existing_car:
                        # Update existing car
                        for key, value in car_data.items():
                            if key != 'first_seen' and hasattr(existing_car, key) and value is not None:
                                setattr(existing_car, key, value)
                        existing_car.last_updated = datetime.utcnow()
                        cars_updated += 1
                    else:
                        # Add new car
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
                        cars_added += 1
                except Exception as e:
                    logger.error(f"Error processing car: {e}")
                    continue

            # Update scraping session
            scraping_session.completed_at = datetime.utcnow()
            scraping_session.status = 'completed'
            scraping_session.cars_found = len(scraped_cars)
            scraping_session.cars_added = cars_added
            scraping_session.cars_updated = cars_updated

            session.commit()

            logger.info(f"{website_name}: {cars_added} new cars, {cars_updated} updated cars")

            return {
                'website': website_name,
                'success': True,
                'cars_found': len(scraped_cars),
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

    async def run_scraping_session(self) -> Dict:
        """Run scraping across all sources"""
        results = []

        # Scrape marktplaats.nl
        try:
            logger.info("=== Starting Marktplaats scraper ===")
            marktplaats = MarktplaatsScraper()
            result = await self._scrape_with_scraper(
                marktplaats, 'marktplaats.nl',
                search_terms=self.search_terms,
                max_pages=3
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Marktplaats scraper failed: {e}")
            results.append({'website': 'marktplaats.nl', 'success': False, 'error': str(e)})

        # Scrape schadeautos.nl
        try:
            logger.info("=== Starting SchadeAutos scraper ===")
            schadeautos = SchadeautosScraper()
            result = await self._scrape_with_scraper(
                schadeautos, 'schadeautos.nl',
                search_terms=[],
                max_pages=5
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
