import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
import logging

class SchadevoertuigenScraper(BaseScraper):
    def __init__(self):
        super().__init__(use_selenium=True)
        self.base_url = "https://www.schadevoertuigen.nl"
        self.search_url = "https://www.schadevoertuigen.nl/zoeken"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        all_cars = []

        # This site is specifically for damaged vehicles, so we'll scrape all listings
        for page in range(1, max_pages + 1):
            page_url = f"{self.search_url}?page={page}"
            html = await self.get_page(page_url)
            if not html:
                continue

            cars = self.extract_car_data(html, self.base_url)
            if not cars:
                break

            all_cars.extend(cars)
            self.logger.info(f"Found {len(cars)} cars on page {page}")

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

        # Find all car listing elements (adjust selector based on actual HTML structure)
        listings = soup.find_all('div', class_=re.compile(r'vehicle|car|listing'))

        if not listings:
            # Try alternative selectors
            listings = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'item'))

        for listing in listings:
            try:
                car = self._extract_single_car(listing, base_url)
                if car and self._is_cosmetic_damage_only(car):
                    cars.append(car)
            except Exception as e:
                self.logger.error(f"Error extracting car data: {e}")
                continue

        return cars

    def _extract_single_car(self, listing, base_url: str) -> Optional[Dict]:
        # Extract URL
        link_elem = listing.find('a', href=True)
        if not link_elem:
            return None

        url = urljoin(base_url, link_elem['href'])

        # Extract title
        title_elem = (listing.find('h2') or listing.find('h3') or
                     listing.find('span', class_=re.compile(r'title|name')))
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract price
        price_elem = listing.find(text=re.compile(r'€')) or listing.find('span', class_=re.compile(r'price'))
        if isinstance(price_elem, str):
            price_text = price_elem
        else:
            price_text = price_elem.get_text(strip=True) if price_elem else ""
        price = self.clean_price(price_text)

        # Extract description
        desc_elem = listing.find('p') or listing.find('div', class_=re.compile(r'description'))
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract image
        img_elem = listing.find('img')
        image_url = None
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src')
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(base_url, image_url)

        # Extract car specifications
        make, model, year, mileage = self._parse_car_details(title, description)

        # Extract damage information
        damage_keywords = self._extract_damage_keywords(title + " " + description)

        return {
            'url': url,
            'source_website': 'schadevoertuigen.nl',
            'title': title,
            'description': description,
            'price': price,
            'make': make,
            'model': model,
            'year': year,
            'mileage': mileage,
            'images': [image_url] if image_url else [],
            'damage_keywords': damage_keywords,
            'damage_description': description,
            'has_cosmetic_damage_only': True
        }

    def _parse_car_details(self, title: str, description: str) -> tuple:
        text = (title + " " + description).lower()

        # Dutch car makes
        car_makes = {
            'volkswagen': 'Volkswagen', 'vw': 'Volkswagen', 'audi': 'Audi',
            'bmw': 'BMW', 'mercedes': 'Mercedes-Benz', 'opel': 'Opel',
            'ford': 'Ford', 'renault': 'Renault', 'peugeot': 'Peugeot',
            'citroën': 'Citroën', 'citroen': 'Citroën', 'toyota': 'Toyota',
            'nissan': 'Nissan', 'honda': 'Honda', 'mazda': 'Mazda',
            'hyundai': 'Hyundai', 'kia': 'Kia', 'volvo': 'Volvo',
            'seat': 'SEAT', 'skoda': 'Škoda', 'fiat': 'Fiat'
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
        mileage_match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*km', text)
        mileage = self.clean_mileage(mileage_match.group(1)) if mileage_match else None

        # Extract model (basic extraction)
        model = None
        if make:
            # Try to find model after make
            make_index = text.find(make.lower())
            if make_index != -1:
                after_make = text[make_index + len(make):].strip()
                model_match = re.search(r'^[\s\-]*([a-z0-9\-\s]+)', after_make)
                if model_match:
                    potential_model = model_match.group(1).strip()
                    if len(potential_model) > 1 and len(potential_model) < 20:
                        model = potential_model.title()

        return make, model, year, mileage

    def _extract_damage_keywords(self, text: str) -> List[str]:
        damage_keywords = [
            # Dutch damage terms (cosmetic)
            'cosmetische schade', 'lichte schade', 'lakschade', 'deukjes', 'krassen',
            'hagelschade', 'parkeerdeuk', 'kleine schade', 'bumperdeuk', 'krasjes',
            'lakbeschadiging', 'oppervlakkige schade', 'kleine deuk', 'deuken',

            # English damage terms (cosmetic)
            'cosmetic damage', 'minor damage', 'paint damage', 'dent', 'scratch',
            'scratches', 'dents', 'minor dent', 'small damage', 'surface damage',

            # General terms
            'schade', 'damage', 'beschadigd', 'damaged'
        ]

        found_keywords = []
        text_lower = text.lower()

        for keyword in damage_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords

    def _is_cosmetic_damage_only(self, car: Dict) -> bool:
        # Since this is a damage vehicle site, we need to filter for cosmetic only
        severe_keywords = [
            'motorschade', 'motor defect', 'versnellingsbak', 'transmissie',
            'frame schade', 'chassis schade', 'water schade', 'brand schade',
            'total loss', 'niet rijdend', 'engine damage', 'gearbox',
            'flood damage', 'fire damage', 'structural damage', 'salvage',
            'accident damage', 'crash', 'airbag', 'ongeluk'
        ]

        text = (car.get('title', '') + " " + car.get('description', '')).lower()

        # Check for severe damage indicators
        for keyword in severe_keywords:
            if keyword in text:
                return False

        # Check for cosmetic damage indicators
        cosmetic_indicators = [
            'cosmetische', 'lichte', 'lakschade', 'deuk', 'kras',
            'bumper', 'cosmetic', 'minor', 'paint', 'scratch', 'dent'
        ]

        for indicator in cosmetic_indicators:
            if indicator in text:
                return True

        # Default to False if no clear indicators
        return False

    async def scrape_car_details(self, car_url: str) -> Optional[Dict]:
        html = await self.get_page(car_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        try:
            details = {}

            # Extract contact information
            contact_info = {}

            # Phone number
            phone_elem = soup.find('a', href=re.compile(r'tel:'))
            if phone_elem:
                contact_info['phone'] = phone_elem.get('href').replace('tel:', '')

            # Email
            email_elem = soup.find('a', href=re.compile(r'mailto:'))
            if email_elem:
                contact_info['email'] = email_elem.get('href').replace('mailto:', '')

            details['contact_info'] = contact_info

            # Additional images
            img_elements = soup.find_all('img')
            images = []
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
                if src and ('jpg' in src or 'jpeg' in src or 'png' in src):
                    if not src.startswith('http'):
                        src = urljoin(car_url, src)
                    images.append(src)

            details['images'] = images

            # Detailed specifications
            spec_container = soup.find('div', class_=re.compile(r'spec|detail|info'))
            if spec_container:
                specs = {}
                # Try to extract key-value pairs
                dt_elements = spec_container.find_all('dt')
                for dt in dt_elements:
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        key = dt.get_text(strip=True)
                        value = dd.get_text(strip=True)
                        specs[key] = value

                details['specifications'] = specs

            return details

        except Exception as e:
            self.logger.error(f"Error scraping car details: {e}")
            return None