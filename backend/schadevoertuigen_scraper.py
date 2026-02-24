#!/usr/bin/env python3
"""
Schadevoertuigen.nl Scraper - Uses existing market data and searches for damaged cars
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

class SchadevoertuigenScraper:
    def __init__(self, headless=True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = None
        self.headless = headless
        self.setup_driver()

        # Target car models with their brand and model for URL construction
        self.target_models = [
            {"brand": "Volkswagen", "model": "polo", "search_term": "volkswagen+polo"},
            {"brand": "Volkswagen", "model": "golf", "search_term": "volkswagen+golf"},
            {"brand": "Volkswagen", "model": "up", "search_term": "volkswagen+up"},
            {"brand": "Opel", "model": "corsa", "search_term": "opel+corsa"},
            {"brand": "Opel", "model": "astra", "search_term": "opel+astra"},
            {"brand": "Toyota", "model": "yaris", "search_term": "toyota+yaris"},
            {"brand": "Toyota", "model": "aygo", "search_term": "toyota+aygo"},
            {"brand": "Ford", "model": "fiesta", "search_term": "ford+fiesta"},
            {"brand": "Renault", "model": "clio", "search_term": "renault+clio"},
            {"brand": "Kia", "model": "picanto", "search_term": "kia+picanto"},
            {"brand": "Fiat", "model": "500", "search_term": "fiat+500"},
            {"brand": "Suzuki", "model": "swift", "search_term": "suzuki+swift"},
            {"brand": "Hyundai", "model": "i10", "search_term": "hyundai+i10"},
            {"brand": "Citroen", "model": "c1", "search_term": "citroen+c1"},
            {"brand": "Peugeot", "model": "107", "search_term": "peugeot+107"},
        ]

        # Market prices from previous analysis (using consistent €3450 as baseline)
        self.market_prices = {
            "volkswagen+polo": 3450,
            "volkswagen+golf": 3450,
            "volkswagen+up": 3450,
            "opel+corsa": 1500,
            "opel+astra": 1500,
            "toyota+yaris": 4500,
            "toyota+aygo": 4500,
            "ford+fiesta": 2248,
            "renault+clio": 1800,
            "kia+picanto": 2850,
            "fiat+500": 3000,  # estimated
            "suzuki+swift": 2499,
            "hyundai+i10": 2500,  # estimated
            "citroen+c1": 2000,  # estimated
            "peugeot+107": 2000,  # estimated
        }

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

    def build_schadevoertuigen_url(self, brand: str, model: str) -> str:
        """Build schadevoertuigen.nl search URL"""
        base_url = "https://www.schadevoertuigen.nl/index.php"

        # Parameters based on the example URL
        params = (
            f"?page=1&category=auto&merk={brand}&"
            f"search%5Btype%5D={model}&"
            f"search%5Btransmission%5D=&"
            f"search%5Bbouwjaar%5D=&"
            f"search%5Bbrandstof%5D=benzine&"
            f"search%5Bprijs%5D=&"
            f"search%5Bmin_prijs%5D=850&"
            f"search%5Bmax_prijs%5D="
        )

        return base_url + params

    def get_profitable_damaged_cars(self, brand: str, model: str, search_term: str) -> List[Dict]:
        """Get damaged cars from schadevoertuigen.nl and filter by profitability"""

        # We'll determine market price per car based on its specific year
        self.logger.info(f"Searching {brand} {model} with year-specific market pricing")

        try:
            # Go to main page first, then submit form
            self.driver.get("https://www.schadevoertuigen.nl/")
            self.random_delay(2, 4)

            # Fill out search form
            from selenium.webdriver.support.ui import Select

            # Select brand
            try:
                brand_select = Select(self.driver.find_element(By.NAME, "merk"))
                brand_select.select_by_value(brand)
            except Exception as e:
                self.logger.error(f"Failed to select brand {brand}: {e}")
                return []

            # Set type/model
            try:
                type_input = self.driver.find_element(By.NAME, "search[type]")
                type_input.clear()
                type_input.send_keys(model)
            except Exception as e:
                self.logger.error(f"Failed to set model {model}: {e}")
                return []

            # Set fuel type to benzine
            try:
                fuel_select = Select(self.driver.find_element(By.NAME, "search[brandstof]"))
                fuel_select.select_by_value("benzine")
            except:
                pass

            # Set minimum price
            try:
                min_price_input = self.driver.find_element(By.NAME, "search[min_prijs]")
                min_price_input.clear()
                min_price_input.send_keys("850")
            except:
                pass

            # Submit form
            try:
                self.driver.execute_script("document.zoek_voertuig.submit();")
                self.random_delay(3, 5)
            except Exception as e:
                self.logger.error(f"Failed to submit form: {e}")
                return []

            self.logger.info(f"Search submitted, URL: {self.driver.current_url}")

            # Find car listings using the correct selector
            listings = self.driver.find_elements(By.CSS_SELECTOR, "[onclick*='location']")
            self.logger.info(f"Found {len(listings)} car listings")

            profitable_cars = []

            for listing in listings:
                try:
                    car = self.extract_car_from_schadevoertuigen_listing(listing, brand, model)
                    if car and car['price'] and car['year']:
                        # Get year-specific market price
                        market_price = self.get_market_price_for_car(brand, model, car['year'])
                        profit_threshold = market_price * 0.75  # 25% cheaper

                        # Check if car is profitable (at least 25% cheaper than market)
                        if car['price'] <= profit_threshold:
                            profit_percentage = ((market_price - car['price']) / market_price) * 100
                            deal_rating = self.calculate_deal_rating(profit_percentage)
                            car['market_price'] = market_price
                            car['profit_percentage'] = profit_percentage
                            car['deal_rating'] = deal_rating
                            profitable_cars.append(car)
                            self.logger.info(f"✅ Profitable car found: {car['title']} - €{car['price']} (market {car['year']}: €{market_price}, profit: {profit_percentage:.1f}%, rating: {deal_rating})")
                        else:
                            self.logger.debug(f"❌ Not profitable: €{car['price']} vs market €{market_price} for {car['year']} {brand} {model}")

                except Exception as e:
                    self.logger.debug(f"Error processing listing: {e}")
                    continue

            return profitable_cars

        except Exception as e:
            self.logger.error(f"Error getting damaged cars for {brand} {model}: {e}")
            return []

    def extract_car_from_schadevoertuigen_listing(self, listing, brand: str, model: str) -> Optional[Dict]:
        """Extract car data from schadevoertuigen.nl listing"""
        try:
            full_text = listing.text
            if not full_text or len(full_text) < 10:
                return None

            # Extract title - format appears to be: Brand Model Details Fuel Year €Price
            parts = full_text.strip().split()
            if len(parts) < 4:
                return None

            # Build title from the text
            title = full_text.strip()

            # Check if this listing contains our target model
            if brand.lower() not in title.lower() or model.lower() not in title.lower():
                return None

            # Get URL from onclick attribute
            onclick_attr = listing.get_attribute("onclick")
            url = None
            if onclick_attr and "location=" in onclick_attr:
                # Extract URL from onclick="location='URL'"
                import re
                url_match = re.search(r"location='([^']+)'", onclick_attr)
                if url_match:
                    url = "https://www.schadevoertuigen.nl" + url_match.group(1)

            if not url:
                return None

            # Extract price - look for € followed by number
            price_match = re.search(r'€\s*([0-9.,]+)', full_text)
            if not price_match:
                return None

            price = self.clean_price(price_match.group())
            if not price or price < 850 or price > 15000:  # Expanded range for schadevoertuigen
                return None

            # Extract year - look for 4-digit year
            year_match = re.search(r'\b(20[0-2][0-9])\b', full_text)
            year = int(year_match.group(1)) if year_match else None

            # Only accept cars from 2010 onwards
            if not year or year < 2010:
                return None

            # Only accept cars with less than 200,000 km (or unknown mileage)
            # if mileage and mileage > 200000:
            #     return None

            # Extract mileage if present
            mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)(?:\s*km|\s*KM)', full_text)
            if mileage_match:
                mileage_text = mileage_match.group(1).replace('.', '').replace(',', '')
                try:
                    mileage = int(mileage_text)
                except:
                    mileage = None
            else:
                mileage = None

            return {
                'url': url,
                'source_website': 'schadevoertuigen.nl',
                'title': title,
                'description': full_text,
                'price': price,
                'make': brand,
                'model': model,
                'year': year,
                'mileage': mileage,
                'location': self.extract_location(full_text),
                'images': [],
                'damage_keywords': ['schade'],
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

    def parse_car_details_schadevoertuigen(self, title: str, description: str) -> Tuple[str, Optional[int], Optional[int]]:
        """Parse car make, year, and mileage from schadevoertuigen.nl"""
        text = (title + " " + description).lower()

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

        return title.split()[0] if title else "", year, mileage

    def extract_location(self, text: str) -> str:
        """Extract location from text"""
        cities = ['amsterdam', 'rotterdam', 'den haag', 'utrecht', 'eindhoven', 'tilburg', 'groningen']
        text_lower = text.lower()

        for city in cities:
            if city in text_lower:
                return city.title()
        return ""

    def calculate_deal_rating(self, profit_percentage: float) -> str:
        """Calculate deal rating based on profit percentage"""
        if profit_percentage >= 60:
            return "excellent"
        elif profit_percentage >= 40:
            return "good"
        elif profit_percentage >= 25:
            return "fair"
        else:
            return "poor"

    def get_market_price_for_car(self, brand: str, model: str, year: int) -> float:
        """Get market price using the new market price service"""
        try:
            from market_price_service import MarketPriceService
            service = MarketPriceService()
            market_price = service.get_market_price(brand, model, year)

            if market_price:
                return market_price

            # Fallback to hardcoded prices if no market data available
            search_term = f"{brand.lower()}+{model.lower()}"
            return self.market_prices.get(search_term, 3000)  # default to 3000

        except Exception as e:
            self.logger.warning(f"Error getting market price, using fallback: {e}")
            search_term = f"{brand.lower()}+{model.lower()}"
            return self.market_prices.get(search_term, 3000)

    def scrape_all_profitable_cars(self, max_results: int = 50) -> List[Dict]:
        """Main method to scrape profitable damaged cars from schadevoertuigen.nl"""
        all_profitable_cars = []

        for model_data in self.target_models:
            if len(all_profitable_cars) >= max_results:
                break

            brand = model_data['brand']
            model = model_data['model']
            search_term = model_data['search_term']

            self.logger.info(f"\n=== Searching {brand} {model} on schadevoertuigen.nl ===")

            # Get profitable damaged cars
            damaged_cars = self.get_profitable_damaged_cars(brand, model, search_term)
            all_profitable_cars.extend(damaged_cars)

            if damaged_cars:
                self.logger.info(f"✅ Found {len(damaged_cars)} profitable cars for {brand} {model}")
            else:
                self.logger.debug(f"No profitable cars for {brand} {model}")

            # Delay between models
            self.random_delay(3, 6)

        self.logger.info(f"\n🎯 Total profitable cars found: {len(all_profitable_cars)}")
        return all_profitable_cars[:max_results]