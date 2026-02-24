from sqlalchemy.orm import sessionmaker
from database.database import engine
from database.models import Car, ScrapingSession
from schadevoertuigen_scraper import SchadevoertuigenScraper
import logging
from datetime import datetime
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ScrapingService:
    def __init__(self):
        self.scraper = None

    def run_scraping_session(self) -> Dict:
        """Run a complete scraping session and save results to database"""
        session = SessionLocal()
        cars_added = 0
        cars_updated = 0

        try:
            # Create scraping session record
            scraping_session = ScrapingSession(
                started_at=datetime.utcnow(),
                website='marktplaats.nl',
                status='running'
            )
            session.add(scraping_session)
            session.commit()

            # Define search terms for damaged cars
            damage_terms = [
                'schade auto',
                'beschadigde auto',
                'lakschade',
                'cosmetische schade',
                'lichte schade',
                'hagelschade',
                'parkeerdeuk'
            ]

            logger.info("Starting scraping session...")

            # Initialize Schadevoertuigen scraper
            self.scraper = SchadevoertuigenScraper(headless=True)

            # Scrape profitable damaged cars from schadevoertuigen.nl
            scraped_cars = self.scraper.scrape_all_profitable_cars(max_results=50)

            logger.info(f"Scraped {len(scraped_cars)} cars from schadevoertuigen.nl")

            # Process each scraped car
            for car_data in scraped_cars:
                existing_car = session.query(Car).filter_by(url=car_data['url']).first()

                if existing_car:
                    # Update existing car
                    for key, value in car_data.items():
                        if key != 'first_seen' and hasattr(existing_car, key):
                            setattr(existing_car, key, value)
                    existing_car.last_updated = datetime.utcnow()
                    cars_updated += 1
                else:
                    # Add new car
                    new_car = Car(
                        url=car_data['url'],
                        source_website=car_data['source_website'],
                        title=car_data['title'],
                        description=car_data['description'],
                        price=car_data['price'],
                        make=car_data['make'],
                        model=car_data['model'],
                        year=car_data['year'],
                        mileage=car_data['mileage'],
                        location=car_data['location'],
                        images=car_data['images'],
                        damage_keywords=car_data['damage_keywords'],
                        has_cosmetic_damage_only=car_data['has_cosmetic_damage_only'],
                        market_price=car_data.get('market_price'),
                        profit_percentage=car_data.get('profit_percentage'),
                        deal_rating=car_data.get('deal_rating'),
                        first_seen=datetime.utcnow(),
                        last_updated=datetime.utcnow(),
                        is_active=True
                    )
                    session.add(new_car)
                    cars_added += 1

            # Update scraping session
            scraping_session.completed_at = datetime.utcnow()
            scraping_session.status = 'completed'
            scraping_session.cars_found = len(scraped_cars)
            scraping_session.cars_added = cars_added
            scraping_session.cars_updated = cars_updated

            session.commit()

            logger.info(f"Scraping completed: {cars_added} new cars, {cars_updated} updated cars")

            return {
                'success': True,
                'cars_found': len(scraped_cars),
                'cars_added': cars_added,
                'cars_updated': cars_updated,
                'session_id': scraping_session.id
            }

        except Exception as e:
            logger.error(f"Scraping session failed: {e}")
            if 'scraping_session' in locals():
                scraping_session.status = 'failed'
                scraping_session.error_message = str(e)
                scraping_session.completed_at = datetime.utcnow()
                session.commit()
            session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # Close selenium driver
            if self.scraper:
                try:
                    self.scraper.close()
                except:
                    pass
            session.close()

def test_scraping():
    """Test the scraping service"""
    service = ScrapingService()
    result = service.run_scraping_session()
    print(f"Scraping result: {result}")
    return result

if __name__ == "__main__":
    test_scraping()