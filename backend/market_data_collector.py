#!/usr/bin/env python3
"""
Market Data Collector - Scrapes non-damaged cars from Marktplaats to establish real market prices
"""
import asyncio
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import sessionmaker
from database.database import engine
from sqlalchemy import text
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import re
from collections import defaultdict

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class MarketDataCollector:
    def __init__(self, headless=True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = None
        self.headless = headless

        # Target car models to collect market data for
        self.target_models = [
            {"brand": "Volkswagen", "model": "Polo"},
            {"brand": "Volkswagen", "model": "Golf"},
            {"brand": "Volkswagen", "model": "Up"},
            {"brand": "Toyota", "model": "Yaris"},
            {"brand": "Toyota", "model": "Aygo"},
            {"brand": "Kia", "model": "Picanto"},
            {"brand": "Fiat", "model": "500"},
            {"brand": "Suzuki", "model": "Swift"},
            {"brand": "Ford", "model": "Fiesta"},
            {"brand": "Renault", "model": "Clio"},
            {"brand": "Opel", "model": "Corsa"},
            {"brand": "Opel", "model": "Astra"},
            {"brand": "Hyundai", "model": "i10"},
            {"brand": "Citroen", "model": "C1"},
            {"brand": "Peugeot", "model": "107"},
        ]

        # Year range to collect data for
        self.min_year = 2010
        self.max_year = 2020

        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome driver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        chrome_options.binary_location = "/usr/bin/chromium"

        try:
            self.driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service("/usr/bin/chromedriver"),
                options=chrome_options
            )
            self.driver.implicitly_wait(10)
            self.logger.info("Chrome driver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise

    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()

    def random_delay(self, min_delay=2, max_delay=5):
        """Random delay to avoid detection"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def collect_market_data_for_model(self, brand: str, model: str, max_cars_per_year: int = 20) -> Dict:
        """Collect market data for a specific car model across years"""
        self.logger.info(f"Collecting market data for {brand} {model}")

        # Build search URL for non-damaged cars
        search_term = f"{brand} {model}".replace(" ", "+")
        base_url = f"https://www.marktplaats.nl/l/auto-s/auto-s/#q:{search_term}"

        all_cars = []

        try:
            # Search for cars without damage keywords
            self.driver.get(base_url)
            self.random_delay(3, 5)

            # Get multiple pages of results
            for page in range(1, 4):  # First 3 pages
                if page > 1:
                    try:
                        # Navigate to next page
                        next_button = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-next']")
                        if next_button.is_enabled():
                            next_button.click()
                            self.random_delay(3, 5)
                        else:
                            break
                    except:
                        break

                # Extract cars from current page
                page_cars = self.extract_cars_from_page()
                filtered_cars = self.filter_non_damaged_cars(page_cars, brand, model)
                all_cars.extend(filtered_cars)

                self.logger.info(f"Page {page}: Found {len(filtered_cars)} non-damaged {brand} {model} cars")

                if len(all_cars) >= max_cars_per_year * (self.max_year - self.min_year + 1):
                    break

        except Exception as e:
            self.logger.error(f"Error collecting data for {brand} {model}: {e}")

        # Group cars by year and calculate averages
        market_data = self.calculate_market_averages(all_cars, brand, model)

        return market_data

    def extract_cars_from_page(self) -> List[Dict]:
        """Extract car listings from current page"""
        cars = []

        try:
            # Wait for listings to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='listing-item']"))
            )

            listings = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='listing-item']")

            for listing in listings:
                try:
                    car = self.extract_car_from_listing(listing)
                    if car:
                        cars.append(car)
                except Exception as e:
                    self.logger.debug(f"Error extracting car: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error extracting cars from page: {e}")

        return cars

    def extract_car_from_listing(self, listing) -> Optional[Dict]:
        """Extract car data from a single listing"""
        try:
            # Get listing HTML
            html = listing.get_attribute('outerHTML')
            soup = BeautifulSoup(html, 'html.parser')

            # Extract title
            title_elem = soup.find(['h3', 'h2'])
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract price
            price_elem = soup.find(text=re.compile(r'€\s*[\d.,]+'))
            price = self.clean_price(price_elem) if price_elem else None

            # Extract year from title
            year_match = re.search(r'\b(20[0-2][0-9])\b', title)
            year = int(year_match.group(1)) if year_match else None

            # Extract mileage
            mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*km', title, re.IGNORECASE)
            mileage = self.clean_mileage(mileage_match.group(1)) if mileage_match else None

            # Only include cars with valid price and year in our range
            if not price or not year or year < self.min_year or year > self.max_year:
                return None

            # Price filtering (reasonable range for used cars)
            if price < 1000 or price > 25000:
                return None

            return {
                'title': title,
                'price': price,
                'year': year,
                'mileage': mileage
            }

        except Exception as e:
            self.logger.debug(f"Error extracting car from listing: {e}")
            return None

    def filter_non_damaged_cars(self, cars: List[Dict], brand: str, model: str) -> List[Dict]:
        """Filter out cars with damage keywords"""
        damage_keywords = [
            'schade', 'damage', 'beschadigd', 'damaged', 'deuk', 'dent', 'kras', 'scratch',
            'ongeluk', 'accident', 'botsen', 'crash', 'herstel', 'repair', 'reparatie',
            'lakschade', 'hagelschade', 'export', 'onderdelen', 'parts', 'defect'
        ]

        filtered_cars = []

        for car in cars:
            title_lower = car['title'].lower()

            # Check if title contains the target brand/model
            if brand.lower() not in title_lower or model.lower() not in title_lower:
                continue

            # Check for damage keywords
            has_damage = any(keyword in title_lower for keyword in damage_keywords)

            if not has_damage:
                filtered_cars.append(car)

        return filtered_cars

    def calculate_market_averages(self, cars: List[Dict], brand: str, model: str) -> Dict:
        """Calculate average prices per year"""
        year_prices = defaultdict(list)

        # Group prices by year
        for car in cars:
            if car['year'] and car['price']:
                year_prices[car['year']].append(car['price'])

        # Calculate averages
        market_data = {}
        for year, prices in year_prices.items():
            if len(prices) >= 3:  # Minimum 3 samples for reliable average
                avg_price = sum(prices) / len(prices)
                market_data[year] = {
                    'average_price': round(avg_price),
                    'sample_count': len(prices),
                    'min_price': min(prices),
                    'max_price': max(prices)
                }
                self.logger.info(f"{brand} {model} {year}: €{avg_price:.0f} (from {len(prices)} cars)")

        return market_data

    def save_market_data(self, brand: str, model: str, market_data: Dict):
        """Save market data to database"""
        session = SessionLocal()

        try:
            for year, data in market_data.items():
                # Insert or update market price data
                upsert_sql = """
                INSERT INTO market_prices (make, model, year, average_price, sample_count, last_updated)
                VALUES (:make, :model, :year, :avg_price, :sample_count, CURRENT_TIMESTAMP)
                ON CONFLICT(make, model, year) DO UPDATE SET
                    average_price = :avg_price,
                    sample_count = :sample_count,
                    last_updated = CURRENT_TIMESTAMP
                """

                session.execute(text(upsert_sql), {
                    'make': brand,
                    'model': model,
                    'year': year,
                    'avg_price': data['average_price'],
                    'sample_count': data['sample_count']
                })

            session.commit()
            self.logger.info(f"✅ Saved market data for {brand} {model}")

        except Exception as e:
            self.logger.error(f"Error saving market data: {e}")
            session.rollback()
        finally:
            session.close()

    def clean_price(self, price_text: str) -> Optional[float]:
        """Clean and convert price text to float"""
        if not price_text:
            return None

        # Remove currency symbols and extract numbers
        price_text = str(price_text).replace("€", "").replace("EUR", "").replace(",-", "")
        price_text = re.sub(r'[^\d.,]', '', price_text)

        if not price_text:
            return None

        # Handle Dutch number format
        if ',' in price_text and '.' in price_text:
            # Format like 12.500,00
            price_text = price_text.replace('.', '').replace(',', '.')
        elif '.' in price_text and not ',' in price_text:
            # Format like 12.500 (thousands separator)
            parts = price_text.split('.')
            if len(parts) == 2 and len(parts[1]) == 3:
                price_text = price_text.replace('.', '')
        elif ',' in price_text:
            parts = price_text.split(',')
            if len(parts[-1]) <= 2:
                # Decimal comma
                price_text = price_text.replace(',', '.')
            else:
                # Thousands comma
                price_text = price_text.replace(',', '')

        try:
            return float(price_text)
        except ValueError:
            return None

    def clean_mileage(self, mileage_text: str) -> Optional[int]:
        """Clean and convert mileage text to int"""
        if not mileage_text:
            return None

        # Remove non-digits except dots and commas
        mileage_text = re.sub(r'[^\d.,]', '', mileage_text)
        mileage_text = mileage_text.replace('.', '').replace(',', '')

        try:
            return int(mileage_text)
        except ValueError:
            return None

    def collect_all_market_data(self):
        """Main method to collect market data for all target models"""
        self.logger.info("Starting market data collection...")

        total_models = len(self.target_models)

        for i, model_data in enumerate(self.target_models, 1):
            brand = model_data['brand']
            model = model_data['model']

            self.logger.info(f"\n=== [{i}/{total_models}] Processing {brand} {model} ===")

            try:
                market_data = self.collect_market_data_for_model(brand, model)
                if market_data:
                    self.save_market_data(brand, model, market_data)
                else:
                    self.logger.warning(f"No market data found for {brand} {model}")

            except Exception as e:
                self.logger.error(f"Error processing {brand} {model}: {e}")

            # Delay between models to be respectful
            if i < total_models:
                self.random_delay(5, 10)

        self.logger.info("✅ Market data collection completed!")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    collector = MarketDataCollector(headless=True)

    try:
        collector.collect_all_market_data()
    finally:
        collector.close()