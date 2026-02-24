#!/usr/bin/env python3
"""
Profitable Car Scraper - Only adds damaged cars that are significantly cheaper than market value
"""
import re
import time
import random
import logging
from typing import List, Dict, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from bs4 import BeautifulSoup

class ProfitableCarScraper:
    def __init__(self, headless=True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = None
        self.headless = headless
        self.setup_driver()

        # Target car models with their brand and model for URL construction
        self.target_models = [
            {"brand": "volkswagen", "model": "polo", "search_term": "volkswagen+polo"},
            {"brand": "volkswagen", "model": "golf", "search_term": "volkswagen+golf"},
            {"brand": "volkswagen", "model": "up", "search_term": "volkswagen+up"},
            {"brand": "opel", "model": "corsa", "search_term": "opel+corsa"},
            {"brand": "opel", "model": "astra", "search_term": "opel+astra"},
            {"brand": "toyota", "model": "yaris", "search_term": "toyota+yaris"},
            {"brand": "toyota", "model": "aygo", "search_term": "toyota+aygo"},
            {"brand": "ford", "model": "fiesta", "search_term": "ford+fiesta"},
            {"brand": "renault", "model": "clio", "search_term": "renault+clio"},
            {"brand": "kia", "model": "picanto", "search_term": "kia+picanto"},
            {"brand": "fiat", "model": "500", "search_term": "fiat+500"},
            {"brand": "suzuki", "model": "swift", "search_term": "suzuki+swift"},
            {"brand": "hyundai", "model": "i10", "search_term": "hyundai+i10"},
            {"brand": "citroen", "model": "c1", "search_term": "citroen+c1"},
            {"brand": "peugeot", "model": "107", "search_term": "peugeot+107"},
        ]

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

    def build_search_url(self, brand: str, search_term: str, year: int = None, with_damage: bool = False) -> str:
        """Build marktplaats search URL with the specified format"""
        base_url = f"https://www.marktplaats.nl/l/auto-s/{brand}/"

        # Add damage keyword if searching for damaged cars
        if with_damage:
            search_term += "+schade"

        # Filters: mileage max 200k, price €1500-7000, specific year or range, sorted by price
        query_params = (
            f"#q:{search_term}|"
            f"mileageTo:200001|"
            f"PriceCentsFrom:150000|"
            f"PriceCentsTo:700000|"
        )

        # Add year filter - either specific year or range
        if year:
            query_params += f"constructionYearFrom:{year}|constructionYearTo:{year}|"
        else:
            query_params += f"constructionYearFrom:2012|constructionYearTo:2025|"

        query_params += f"sortBy:PRICE|sortOrder:INCREASING"

        return base_url + query_params

    def get_market_prices_by_year(self, brand: str, search_term: str, year: int, max_cars: int = 5) -> List[float]:
        """Get lowest prices for non-damaged cars of a specific year"""
        search_url = self.build_search_url(brand, search_term, year=year, with_damage=False)
        self.logger.info(f"Analyzing {year} market prices for {search_term}: {search_url}")

        try:
            self.driver.get(search_url)
            self.random_delay(3, 6)

            # Accept cookies if present
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepteren') or contains(text(), 'Accept')]"))
                )
                cookie_button.click()
                self.random_delay(2, 4)
            except:
                pass

            # Find car listings
            listings = self.driver.find_elements(By.CSS_SELECTOR, ".hz-Listing")
            prices = []

            for i, listing in enumerate(listings[:max_cars]):
                try:
                    full_text = listing.text
                    self.logger.debug(f"Listing {i+1} text: {full_text[:100]}...")

                    price_match = re.search(r'€\s*([0-9.,]+),-?', full_text)
                    if price_match:
                        price_text = price_match.group()
                        price = self.clean_price(price_text)
                        self.logger.debug(f"Raw price: {price_text} -> Cleaned: {price}")

                        if price and 1500 <= price <= 7000:  # Within our target range
                            prices.append(price)
                            self.logger.info(f"✅ Found {year} market price: €{price}")
                        else:
                            self.logger.debug(f"Price €{price} outside range 1500-7000")
                    else:
                        self.logger.debug(f"No price found in listing {i+1}")

                except Exception as e:
                    self.logger.error(f"Error extracting price from listing {i}: {e}")
                    continue

            prices.sort()  # Sort by price
            self.logger.info(f"Market analysis for {search_term} {year}: {len(prices)} cars, lowest prices: {prices[:3]}")
            return prices

        except Exception as e:
            self.logger.error(f"Error getting market prices for {search_term} {year}: {e}")
            return []

    def get_damaged_cars_by_year(self, brand: str, search_term: str, year: int, lowest_market_price: float) -> List[Dict]:
        """Get damaged cars of specific year and filter by profitability"""
        # Calculate profit threshold (30% cheaper than lowest market price)
        profit_threshold = lowest_market_price * 0.7  # 30% cheaper

        self.logger.info(f"Searching {year} damaged cars for {search_term}: market €{lowest_market_price:.0f}, profit threshold: €{profit_threshold:.0f}")

        search_url = self.build_search_url(brand, search_term, year=year, with_damage=True)
        self.logger.info(f"Damaged car URL: {search_url}")

        try:
            self.driver.get(search_url)
            self.random_delay(3, 6)

            # Find car listings
            listings = self.driver.find_elements(By.CSS_SELECTOR, ".hz-Listing")
            profitable_cars = []

            for listing in listings:
                try:
                    car = self.extract_car_from_listing(listing, search_term)
                    if car and car['price'] and car['year'] == year:  # Ensure year matches
                        # Check if car is profitable (at least 30% cheaper than market)
                        if car['price'] <= profit_threshold:
                            profit_percentage = ((lowest_market_price - car['price']) / lowest_market_price) * 100
                            car['market_price'] = lowest_market_price
                            car['profit_percentage'] = profit_percentage
                            profitable_cars.append(car)
                            self.logger.info(f"✅ Profitable {year} car found: {car['title']} - €{car['price']} (market: €{lowest_market_price}, profit: {profit_percentage:.1f}%)")
                        else:
                            self.logger.debug(f"❌ Not profitable: €{car['price']} vs market €{lowest_market_price}")

                except Exception as e:
                    self.logger.debug(f"Error processing listing: {e}")
                    continue

            return profitable_cars

        except Exception as e:
            self.logger.error(f"Error getting damaged cars for {search_term} {year}: {e}")
            return []

    def extract_car_from_listing(self, listing, model_name: str) -> Optional[Dict]:
        """Extract car data from listing"""
        try:
            full_text = listing.text
            if not full_text or len(full_text) < 10:
                return None

            # Extract title
            lines = full_text.split('\n')
            title = lines[0] if lines else ""

            if not title or len(title) < 5:
                return None

            # Filter out unwanted listings
            title_lower = title.lower()
            exclude_keywords = ['inkoop', 'gezocht', 'gevraagd', 'auctim', 'onderdelen', 'parts']
            if any(keyword in title_lower for keyword in exclude_keywords):
                return None

            # Get URL
            try:
                link_elem = listing.find_element(By.TAG_NAME, "a")
                url = link_elem.get_attribute("href")
                if not url or 'marktplaats.nl' not in url:
                    return None
            except:
                return None

            # Extract price
            price_match = re.search(r'€\s*([0-9.,]+),-?', full_text)
            if not price_match:
                return None

            price = self.clean_price(price_match.group())
            if not price or price < 1500 or price > 7000:
                return None

            # Extract other details
            make, model, year, mileage = self.parse_car_details(title, full_text, model_name)

            return {
                'url': url,
                'source_website': 'marktplaats.nl',
                'title': title,
                'description': full_text[:500],
                'price': price,
                'make': make,
                'model': model,
                'year': year,
                'mileage': mileage,
                'location': self.extract_location(full_text),
                'images': [],
                'damage_keywords': ['schade'],  # We know it has damage since we searched for it
                'has_cosmetic_damage_only': True,
                'is_profitable': True
            }

        except Exception as e:
            self.logger.debug(f"Error extracting car: {e}")
            return None

    def clean_price(self, price_text: str) -> Optional[float]:
        """Clean and convert price text to float"""
        if not price_text:
            return None

        # Remove currency symbols and dash
        price_text = str(price_text).replace("€", "").replace("EUR", "").replace(",-", "")
        price_text = re.sub(r'[^\d.,]', '', price_text)

        if not price_text:
            return None

        # Handle Dutch number format (e.g., 2.900 or 2.900,50)
        if ',' in price_text and '.' in price_text:
            # Format like 2.900,50 - remove thousands separator, keep decimal
            price_text = price_text.replace('.', '').replace(',', '.')
        elif '.' in price_text and not ',' in price_text:
            # Format like 2.900 - this is thousands separator in Dutch
            # Check if likely thousands separator (3 digits after)
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

    def parse_car_details(self, title: str, description: str, model_name: str) -> Tuple[str, str, Optional[int], Optional[int]]:
        """Parse car make, model, year, and mileage"""
        text = (title + " " + description).lower()

        # Extract make from model_name
        make_mapping = {
            'volkswagen': 'Volkswagen',
            'opel': 'Opel',
            'toyota': 'Toyota',
            'ford': 'Ford',
            'renault': 'Renault',
            'kia': 'Kia',
            'fiat': 'Fiat',
            'suzuki': 'Suzuki',
            'hyundai': 'Hyundai',
            'citroen': 'Citroën',
            'peugeot': 'Peugeot'
        }

        make = None
        for brand_key, brand_name in make_mapping.items():
            if brand_key in model_name.lower():
                make = brand_name
                break

        # Extract model from model_name
        model = model_name.split('+')[-1].title()  # Get last part and capitalize

        # Extract year
        year_match = re.search(r'\b(20[0-2][0-9])\b', text)
        year = int(year_match.group(1)) if year_match else None

        # Extract mileage
        mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*km', text)
        if mileage_match:
            mileage_text = mileage_match.group(1).replace('.', '').replace(',', '')
            try:
                mileage = int(mileage_text)
            except:
                mileage = None
        else:
            mileage = None

        return make, model, year, mileage

    def extract_location(self, text: str) -> str:
        """Extract location from text"""
        cities = ['amsterdam', 'rotterdam', 'den haag', 'utrecht', 'eindhoven', 'tilburg', 'groningen']
        text_lower = text.lower()

        for city in cities:
            if city in text_lower:
                return city.title()
        return ""

    def scrape_profitable_cars(self, max_results: int = 50) -> List[Dict]:
        """Main method to scrape profitable damaged cars year by year"""
        all_profitable_cars = []

        for model_data in self.target_models:
            if len(all_profitable_cars) >= max_results:
                break

            brand = model_data['brand']
            search_term = model_data['search_term']

            self.logger.info(f"\\n=== Analyzing {search_term.replace('+', ' ').title()} ===")

            # Analyze each year from 2012 to 2025
            for year in range(2012, 2026):  # 2012-2025 inclusive
                if len(all_profitable_cars) >= max_results:
                    break

                self.logger.info(f"📅 Analyzing {year} {search_term.replace('+', ' ').title()}")

                # Step 1: Get market prices for non-damaged cars of this year
                market_prices = self.get_market_prices_by_year(brand, search_term, year)

                if market_prices:
                    # Use lowest market price for this year
                    lowest_market_price = min(market_prices)

                    # Step 2: Find profitable damaged cars for this year
                    damaged_cars = self.get_damaged_cars_by_year(brand, search_term, year, lowest_market_price)
                    all_profitable_cars.extend(damaged_cars)

                    if damaged_cars:
                        self.logger.info(f"✅ Found {len(damaged_cars)} profitable {year} cars for {search_term}")
                    else:
                        self.logger.debug(f"No profitable {year} cars for {search_term}")
                else:
                    self.logger.debug(f"No {year} market data for {search_term}")

                # Short delay between years
                self.random_delay(2, 4)

            # Longer delay between models
            self.random_delay(5, 8)

        self.logger.info(f"\\n🎯 Total profitable cars found: {len(all_profitable_cars)}")
        return all_profitable_cars[:max_results]