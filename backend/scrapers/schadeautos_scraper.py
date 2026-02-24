import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
import logging


class SchadeautosScraper(BaseScraper):
    def __init__(self):
        super().__init__(use_selenium=True)
        self.base_url = "https://www.schadeautos.nl"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        all_cars = []

        # Scrape the main personenautos listing page
        url = f"{self.base_url}/nl/schade/personenautos"
        self.logger.info(f"Scraping {url}")

        html = await self.get_page(url)
        if html:
            cars = self.extract_car_data(html, self.base_url)
            all_cars.extend(cars)
            self.logger.info(f"Found {len(cars)} cars on main page")

            # Try to click "load more" or scroll for more results via Selenium
            if self.driver:
                try:
                    from selenium.webdriver.common.by import By
                    import time

                    # Scroll down to trigger lazy loading
                    for _ in range(3):
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)

                    # Get updated page source after scrolling
                    updated_html = self.driver.page_source
                    more_cars = self.extract_car_data(updated_html, self.base_url)
                    if len(more_cars) > len(cars):
                        all_cars = more_cars
                        self.logger.info(f"Found {len(more_cars)} cars after scrolling")
                except Exception as e:
                    self.logger.error(f"Error during scroll loading: {e}")

        # Remove duplicates based on URL
        seen_urls = set()
        unique_cars = []
        for car in all_cars:
            if car.get('url') and car['url'] not in seen_urls:
                seen_urls.add(car['url'])
                unique_cars.append(car)

        return unique_cars

    def extract_car_data(self, html: str, base_url: str = "") -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        cars = []

        # SchadeAutos uses <a> tags linking to /nl/schade/personenautos/... with <h2> titles
        # Find all links that point to individual car pages
        car_links = soup.find_all('a', href=re.compile(r'/nl/schade/personenautos/.+/o/\d+'))

        self.logger.info(f"Found {len(car_links)} car link elements")

        for link in car_links:
            try:
                car = self._extract_single_car(link, base_url)
                if car:
                    cars.append(car)
            except Exception as e:
                self.logger.error(f"Error extracting car data: {e}")
                continue

        return cars

    def _extract_single_car(self, link_elem, base_url: str) -> Optional[Dict]:
        url = urljoin(base_url, link_elem.get('href', ''))
        if not url:
            return None

        # Get all text content
        full_text = link_elem.get_text(separator=' ', strip=True)
        if not full_text or len(full_text) < 5:
            return None

        # Extract title from <h2> tag
        title_elem = link_elem.find('h2')
        title = title_elem.get_text(strip=True) if title_elem else full_text.split('€')[0].strip()

        # Extract price - look for € symbol
        price = None
        price_matches = re.findall(r'€\s*([\d.,]+)', full_text)
        if price_matches:
            # Take the first non-export price (usually the main/higher price)
            for pm in price_matches:
                p = self._parse_dutch_price(pm)
                if p and p > 0:
                    price = p
                    break

        # Extract year from text (look for 4-digit year)
        year = None
        year_match = re.search(r'\b(19[89]\d|20[0-2]\d)\b', full_text)
        if year_match:
            year = int(year_match.group(1))

        # Extract mileage
        mileage = None
        mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:km|KM)', full_text)
        if mileage_match:
            mileage_text = mileage_match.group(1).replace('.', '').replace(',', '')
            try:
                mileage = int(mileage_text)
            except ValueError:
                pass

        # Extract fuel type
        fuel_keywords = {'benzine': 'Benzine', 'diesel': 'Diesel', 'elektrisch': 'Elektrisch',
                        'hybride': 'Hybride', 'lpg': 'LPG'}
        fuel_type = None
        text_lower = full_text.lower()
        for key, value in fuel_keywords.items():
            if key in text_lower:
                fuel_type = value
                break

        # Extract image
        img_elem = link_elem.find('img')
        image_url = None
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src')
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(base_url, image_url)

        # Parse make and model from title
        make, model = self._parse_make_model(title)

        return {
            'url': url,
            'source_website': 'schadeautos.nl',
            'title': title,
            'description': full_text,
            'price': price,
            'make': make,
            'model': model,
            'year': year,
            'mileage': mileage,
            'fuel_type': fuel_type,
            'location': '',
            'images': [image_url] if image_url else [],
            'damage_keywords': ['schade'],
            'has_cosmetic_damage_only': True,
        }

    def _parse_dutch_price(self, price_text: str) -> Optional[float]:
        """Parse Dutch price format: 2.750 or 12.350"""
        if not price_text:
            return None
        # Remove dots (thousand separators) and replace comma with dot for decimals
        cleaned = price_text.replace('.', '').replace(',', '.')
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_make_model(self, title: str) -> tuple:
        """Extract make and model from title like 'Volkswagen Polo 1.0 TSI Highline'"""
        car_makes = {
            'volkswagen': 'Volkswagen', 'vw': 'Volkswagen', 'audi': 'Audi',
            'bmw': 'BMW', 'mercedes': 'Mercedes-Benz', 'mercedes-benz': 'Mercedes-Benz',
            'opel': 'Opel', 'ford': 'Ford', 'renault': 'Renault', 'peugeot': 'Peugeot',
            'citroën': 'Citroën', 'citroen': 'Citroën', 'toyota': 'Toyota',
            'nissan': 'Nissan', 'honda': 'Honda', 'mazda': 'Mazda',
            'hyundai': 'Hyundai', 'kia': 'Kia', 'volvo': 'Volvo',
            'seat': 'SEAT', 'skoda': 'Škoda', 'fiat': 'Fiat',
            'alfa romeo': 'Alfa Romeo', 'mini': 'MINI', 'smart': 'Smart',
            'dacia': 'Dacia', 'suzuki': 'Suzuki', 'mitsubishi': 'Mitsubishi',
            'porsche': 'Porsche', 'tesla': 'Tesla', 'land rover': 'Land Rover',
            'jaguar': 'Jaguar', 'jeep': 'Jeep', 'chrysler': 'Chrysler',
        }

        title_lower = title.lower()
        make = None
        model = None

        for key, value in car_makes.items():
            if title_lower.startswith(key) or f' {key} ' in f' {title_lower} ':
                make = value
                # Try to extract model: word(s) after the make
                after_make = title_lower.split(key, 1)[1].strip() if key in title_lower else ''
                if after_make:
                    # Model is usually the next word(s) before version numbers
                    model_match = re.match(r'^([a-z0-9\-]+)', after_make)
                    if model_match:
                        model = model_match.group(1).title()
                break

        return make, model

    async def scrape_car_details(self, car_url: str) -> Optional[Dict]:
        html = await self.get_page(car_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        try:
            details = {}

            # Extract all images
            img_elements = soup.find_all('img')
            images = []
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
                if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    if not src.startswith('http'):
                        src = urljoin(car_url, src)
                    images.append(src)
            details['images'] = list(set(images))

            return details

        except Exception as e:
            self.logger.error(f"Error scraping car details: {e}")
            return None
