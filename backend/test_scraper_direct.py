#!/usr/bin/env python3
"""
Direct test of the selenium scraper to debug the timeout issue
"""
import logging
import time
from selenium_scraper import SeleniumScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_scraper_with_timeout():
    """Test the scraper with timeout handling"""
    scraper = None
    try:
        logger.info("Starting direct scraper test...")
        scraper = SeleniumScraper(headless=True)

        logger.info("Scraper initialized, starting scraping...")
        start_time = time.time()

        # Test with target parameters
        cars = scraper.scrape_marktplaats_budget_cars(
            min_price=1500,
            max_price=5000,
            max_results=50  # Target 50 cars
        )

        elapsed_time = time.time() - start_time
        logger.info(f"Scraping completed in {elapsed_time:.2f} seconds")
        logger.info(f"Found {len(cars)} cars")

        for i, car in enumerate(cars, 1):
            logger.info(f"{i}. {car['title'][:50]}... - €{car['price']} - {car['url']}")

        return cars

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return []
    finally:
        if scraper:
            logger.info("Closing scraper...")
            scraper.close()

if __name__ == "__main__":
    test_scraper_with_timeout()