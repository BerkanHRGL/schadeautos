#!/usr/bin/env python3
"""
Script to clean up poor quality car listings from the database
"""
from sqlalchemy.orm import sessionmaker
from database.database import engine
from database.models import Car
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_database():
    """Remove poor quality car listings"""
    session = SessionLocal()

    try:
        # Keywords to identify poor quality listings
        bad_keywords = [
            'INKOOP', 'GEZOCHT', 'Sprinter', 'Crafter', 'Transit', 'Iveco',
            'bestelauto', 'bestelwagen', 'vrachtwagen', 'truck', 'lease'
        ]

        deleted_count = 0

        # Get all cars
        cars = session.query(Car).all()
        logger.info(f"Found {len(cars)} total cars in database")

        for car in cars:
            title_lower = car.title.lower() if car.title else ""
            desc_lower = car.description.lower() if car.description else ""
            text = title_lower + " " + desc_lower

            # Check if car should be deleted
            should_delete = False

            # Check for bad keywords
            for keyword in bad_keywords:
                if keyword.lower() in text:
                    should_delete = True
                    logger.info(f"Deleting car with keyword '{keyword}': {car.title}")
                    break

            # Check for suspiciously low prices (likely lease monthly payments)
            if car.price and car.price < 1300:
                should_delete = True
                logger.info(f"Deleting car with low price €{car.price}: {car.title}")

            # Check for missing or empty titles
            if not car.title or len(car.title.strip()) < 10:
                should_delete = True
                logger.info(f"Deleting car with poor title: {car.title}")

            if should_delete:
                session.delete(car)
                deleted_count += 1

        session.commit()

        remaining_cars = session.query(Car).count()
        logger.info(f"Cleanup completed: Deleted {deleted_count} cars, {remaining_cars} cars remaining")

        # Show sample of remaining cars
        sample_cars = session.query(Car).limit(5).all()
        logger.info("Sample of remaining cars:")
        for car in sample_cars:
            logger.info(f"- {car.title} - €{car.price} - {car.make}")

        return {"deleted": deleted_count, "remaining": remaining_cars}

    except Exception as e:
        session.rollback()
        logger.error(f"Error during cleanup: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    result = cleanup_database()
    print(f"Cleanup result: {result}")