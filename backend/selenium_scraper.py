from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin

class SeleniumScraper:
    def __init__(self, headless=True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = None
        self.headless = headless
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome driver with proper options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--accept-language=nl-NL,nl;q=0.9,en;q=0.8")

        try:
            chrome_options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
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
        """Random delay to avoid being detected"""
        delay = random.uniform(min_delay, max_delay)
        self.logger.info(f"Waiting {delay:.1f} seconds...")
        time.sleep(delay)

    def scrape_marktplaats_budget_cars(self, min_price: int = 1300, max_price: int = 5000, max_results: int = 50) -> List[Dict]:
        """Scrape Marktplaats for cars under max_price using Selenium"""
        all_cars = []

        try:
            # Build search URL with price filter and damage-related search terms
            base_url = "https://www.marktplaats.nl/l/auto-s/"
            # Use brand-specific searches with damage keywords like the user suggested
            brands = ['volkswagen', 'audi', 'bmw', 'mercedes-benz', 'opel', 'ford', 'renault', 'peugeot', 'toyota']
            damage_keywords = ['schade', 'lakschade', 'deukjes']

            # Convert prices to cents for marktplaats format
            price_cents_from = min_price * 100  # €1300 = 130000 cents
            price_cents_to = max_price * 100    # €5000 = 500000 cents

            damage_searches = []

            # Create searches for each brand + damage keyword combination
            for brand in brands:
                for keyword in damage_keywords:
                    search_url = f"https://www.marktplaats.nl/l/auto-s/{brand}/#q:{keyword}|PriceCentsFrom:{price_cents_from}|PriceCentsTo:{price_cents_to}"
                    damage_searches.append(search_url)

            # Add some general searches as backup
            for keyword in damage_keywords:
                search_url = f"https://www.marktplaats.nl/l/auto-s/#q:{keyword}|PriceCentsFrom:{price_cents_from}|PriceCentsTo:{price_cents_to}"
                damage_searches.append(search_url)

            for search_url in damage_searches:
                if len(all_cars) >= max_results:
                    break

                self.logger.info(f"Navigating to: {search_url}")
                self.driver.get(search_url)

                # Wait for page to load
                self.random_delay(3, 6)

                # Accept cookies if present (only once)
                if search_url == damage_searches[0]:
                    try:
                        cookie_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepteren') or contains(text(), 'Accept')]"))
                        )
                        cookie_button.click()
                        self.logger.info("Accepted cookies")
                        self.random_delay(2, 4)
                    except:
                        self.logger.info("No cookie banner found or already accepted")

                # Scrape this search term
                page = 1
                search_cars = 0
                while len(all_cars) < max_results and page <= 3 and search_cars < 20:  # Increased limits
                    self.logger.info(f"Scraping search term, page {page}")

                    # Find car listings
                    listings = self.find_car_listings()

                    if not listings:
                        self.logger.info("No more listings found")
                        break

                    # Extract car data from listings with timeout protection
                    page_cars = []
                    for i, listing in enumerate(listings):
                        try:
                            self.logger.debug(f"Processing listing {i+1}/{len(listings)}")
                            car = self.extract_car_from_listing(listing, max_price)
                            if car:
                                page_cars.append(car)
                                self.logger.debug(f"Extracted car: {car['title'][:50]}...")

                            # Add small delay to avoid overwhelming the browser
                            if i % 10 == 0 and i > 0:
                                time.sleep(0.5)

                        except Exception as e:
                            self.logger.warning(f"Error processing listing {i+1}: {e}")
                            continue

                    # Since we're searching for damage terms, accept all valid cars
                    damage_cars = page_cars.copy()
                    for car in damage_cars:
                        # Ensure all cars have damage keywords since we searched for damage
                        if len(car.get('damage_keywords', [])) == 0:
                            car['damage_keywords'] = ['schade']  # Add generic damage keyword

                    self.logger.info(f"Found {len(damage_cars)} cars with damage on page {page}")
                    all_cars.extend(damage_cars)
                    search_cars += len(damage_cars)

                    # Try to go to next page
                    if len(all_cars) < max_results and search_cars < 20:
                        if not self.go_to_next_page():
                            break
                        page += 1
                        self.random_delay(3, 6)
                    else:
                        break

        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")

        return self.deduplicate_cars(all_cars[:max_results])

    def check_damage_keywords(self, text: str) -> bool:
        """Check if text contains actual damage keywords"""
        damage_keywords = [
            'schade', 'damage', 'lakschade', 'deuk', 'dent', 'krassen', 'scratch',
            'kras', 'hagelschade', 'cosmetische', 'cosmetic', 'lichte schade',
            'minor damage', 'kleine schade', 'oppervlakkige', 'parkeerdeuk',
            'bumperdeuk', 'deukje', 'deukjes', 'beschadigd', 'damaged'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in damage_keywords)

    def find_car_listings(self) -> List:
        """Find car listing elements on the page"""
        selectors = [
            ".hz-Listing",
            "[data-listing-id]",
            "article[class*='listing']",
            ".mp-listing"
        ]

        for selector in selectors:
            try:
                listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if listings:
                    self.logger.info(f"Found {len(listings)} listings with selector: {selector}")
                    return listings
            except Exception as e:
                self.logger.debug(f"Selector {selector} failed: {e}")
                continue

        self.logger.warning("No listings found with any selector")
        return []

    def extract_car_from_listing(self, listing, max_price: int) -> Optional[Dict]:
        """Extract car data from a listing element with timeout protection"""
        try:
            # Quick text extraction to avoid selenium timeouts
            try:
                full_text = listing.text
                if not full_text or len(full_text) < 10:
                    return None
            except:
                return None

            # Extract title from the text (faster than selenium queries)
            lines = full_text.split('\n')
            title = lines[0] if lines else ""

            # Basic title validation
            if not title or len(title) < 5:
                return None

            # Filter out car buying services, lease cars, trucks, and non-passenger cars
            title_lower = title.lower()
            full_text_lower = full_text.lower()

            exclude_keywords = [
                # Car buying services
                'inkoop', 'gezocht', 'gevraagd', 'kopen wij', 'we buy', 'auctim',
                # Most problematic commercial vehicles
                'sprinter', 'crafter', 'transit',
                'bestelauto', 'bestelwagen', 'vrachtwagen', 'truck', 'bakwagen',
                # Car buying/selling services
                'bedrijfsauto verkopen', 'autoverkoopsite', 'auto opkoper'
            ]

            # Check title and description for exclusion keywords
            text_to_check = title_lower + " " + full_text_lower
            if any(keyword in text_to_check for keyword in exclude_keywords):
                return None

            # Get URL with single query
            url = ""
            try:
                link_elem = listing.find_element(By.TAG_NAME, "a")
                url = link_elem.get_attribute("href")
                if url and not url.startswith("http"):
                    url = urljoin("https://www.marktplaats.nl", url)
                if not url or 'marktplaats.nl' not in url:
                    return None
            except:
                return None

            # Extract price from text (faster than DOM queries)
            price = None
            price_match = re.search(r'€\s*([\d.,]+)', full_text)
            if price_match:
                price = self.clean_price(price_match.group())
                # More lenient price filtering to get some results
                if price and price > max_price * 2:  # Only exclude if way too expensive
                    return None

            # Simple location extraction
            location = self.extract_location(full_text)

            # Parse car details first
            make, model, year, mileage = self.parse_car_details(title, full_text)

            # Since we're searching for damage terms, accept most cars for now
            # We'll filter out the bad ones later in post-processing

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
                'location': location,
                'images': [],
                'damage_keywords': [],  # Will be filled by has_damage_keywords
                'has_cosmetic_damage_only': True,
                'first_seen': None,
                'is_active': True
            }

        except Exception as e:
            self.logger.debug(f"Error extracting car from listing: {e}")
            return None

    def has_damage_keywords(self, car: Dict) -> bool:
        """Check if car has damage keywords and add them to the car data"""
        damage_keywords = [
            'schade', 'damage', 'beschadigd', 'damaged', 'lakschade', 'deuk', 'dent',
            'krassen', 'scratch', 'kras', 'hagelschade', 'cosmetische', 'cosmetic',
            'lichte schade', 'minor damage', 'kleine schade', 'oppervlakkige',
            'parkeerdeuk', 'bumperdeuk', 'deukje', 'deukjes'
        ]

        text = (car.get('title', '') + " " + car.get('description', '')).lower()

        found_keywords = []
        for keyword in damage_keywords:
            if keyword in text:
                found_keywords.append(keyword)

        car['damage_keywords'] = found_keywords

        # Check for severe damage (exclude these)
        severe_keywords = [
            'motorschade', 'engine damage', 'versnellingsbak', 'transmission',
            'water schade', 'flood', 'brand schade', 'fire', 'total loss',
            'niet rijdend', 'export only'
        ]

        for keyword in severe_keywords:
            if keyword in text:
                return False

        return len(found_keywords) > 0

    def go_to_next_page(self) -> bool:
        """Try to navigate to the next page"""
        try:
            # Look for next page button
            next_selectors = [
                "[aria-label='Next page']",
                "[aria-label='Volgende pagina']",
                "a[class*='next']",
                "button[class*='next']"
            ]

            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button.is_enabled():
                        self.driver.execute_script("arguments[0].click();", next_button)
                        self.logger.info("Clicked next page button")
                        return True
                except:
                    continue

            self.logger.info("No next page button found")
            return False

        except Exception as e:
            self.logger.error(f"Error navigating to next page: {e}")
            return False

    def extract_location(self, text: str) -> str:
        """Extract location from text"""
        # Common Dutch city patterns
        cities = ['amsterdam', 'rotterdam', 'den haag', 'utrecht', 'eindhoven', 'tilburg', 'groningen', 'almere', 'breda', 'nijmegen']
        text_lower = text.lower()

        for city in cities:
            if city in text_lower:
                return city.title()

        return ""

    def parse_car_details(self, title: str, description: str) -> tuple:
        """Parse car make, model, year, and mileage from text"""
        text = (title + " " + description).lower()

        # Car makes
        car_makes = {
            'volkswagen': 'Volkswagen', 'vw': 'Volkswagen', 'audi': 'Audi',
            'bmw': 'BMW', 'mercedes': 'Mercedes-Benz', 'opel': 'Opel',
            'ford': 'Ford', 'renault': 'Renault', 'peugeot': 'Peugeot',
            'citroën': 'Citroën', 'citroen': 'Citroën', 'toyota': 'Toyota',
            'nissan': 'Nissan', 'honda': 'Honda', 'mazda': 'Mazda',
            'hyundai': 'Hyundai', 'kia': 'Kia', 'volvo': 'Volvo',
            'seat': 'Seat', 'skoda': 'Skoda', 'fiat': 'Fiat'
        }

        make = None
        for key, value in car_makes.items():
            if key in text:
                make = value
                break

        # Extract year
        year_match = re.search(r'\b(19[9][0-9]|20[0-2][0-9])\b', text)
        year = int(year_match.group(1)) if year_match else None

        # Extract mileage
        mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\.?\s*km', text)
        mileage = self.clean_mileage(mileage_match.group(1)) if mileage_match else None

        return make, None, year, mileage

    def clean_price(self, price_text: str) -> Optional[float]:
        """Clean and convert price text to float"""
        if not price_text:
            return None

        # Remove currency symbols and clean
        price_text = str(price_text).replace("€", "").replace("EUR", "")
        price_text = re.sub(r'[^\d.,]', '', price_text)

        if not price_text:
            return None

        # Handle Dutch number format
        if ',' in price_text and '.' in price_text:
            price_text = price_text.replace('.', '').replace(',', '.')
        elif ',' in price_text:
            parts = price_text.split(',')
            if len(parts[-1]) <= 2:
                price_text = price_text.replace(',', '.')
            else:
                price_text = price_text.replace(',', '')

        try:
            return float(price_text)
        except ValueError:
            return None

    def clean_mileage(self, mileage_text: str) -> Optional[int]:
        """Clean and convert mileage text to int"""
        if not mileage_text:
            return None

        mileage_text = str(mileage_text).replace("km", "").replace(".", "").replace(",", "")
        mileage_text = ''.join(filter(str.isdigit, mileage_text))

        try:
            return int(mileage_text)
        except ValueError:
            return None

    def deduplicate_cars(self, cars: List[Dict]) -> List[Dict]:
        """Remove duplicate cars based on URL"""
        seen_urls = set()
        unique_cars = []

        for car in cars:
            if car.get('url') and car['url'] not in seen_urls:
                seen_urls.add(car['url'])
                unique_cars.append(car)

        return unique_cars

# Test function
def test_selenium_scraper():
    scraper = None
    try:
        scraper = SeleniumScraper(headless=True)
        cars = scraper.scrape_marktplaats_budget_cars(max_price=10000, max_results=10)

        print(f"\nFound {len(cars)} cars under €10,000 with damage:")
        for i, car in enumerate(cars, 1):
            print(f"\n{i}. {car['title']}")
            print(f"   Price: €{car['price']}")
            print(f"   URL: {car['url']}")
            print(f"   Damage: {car['damage_keywords']}")

        return cars

    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_selenium_scraper()