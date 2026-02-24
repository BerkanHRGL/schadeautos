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
        self.search_url = "https://www.schadeautos.nl/autos"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        all_cars = []

        # This site is specifically for damaged cars, so we scrape all listings
        for page in range(1, max_pages + 1):
            page_url = f"{self.search_url}?pagina={page}"
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

        # Find all car listing elements
        listings = (soup.find_all('div', class_=re.compile(r'auto|car|vehicle|listing')) or
                   soup.find_all('article') or
                   soup.find_all('div', class_=re.compile(r'item|product')))

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
        title_elem = (listing.find('h1') or listing.find('h2') or listing.find('h3') or
                     listing.find(class_=re.compile(r'title|name|heading')))
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract price
        price_elem = (listing.find(string=re.compile(r'€\s*\d')) or
                     listing.find(class_=re.compile(r'price|prijs')))

        if isinstance(price_elem, str):
            price_text = price_elem
        else:
            price_text = price_elem.get_text(strip=True) if price_elem else ""

        price = self.clean_price(price_text)

        # Extract description
        desc_elem = (listing.find('p') or
                    listing.find(class_=re.compile(r'description|desc|summary')))
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract image
        img_elem = listing.find('img')
        image_url = None
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy')
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(base_url, image_url)

        # Extract additional info
        info_elements = listing.find_all(string=re.compile(r'\d{4}|\d+\s*km|km'))
        additional_info = " ".join([elem.strip() for elem in info_elements])

        # Parse car details
        make, model, year, mileage = self._parse_car_details(title, description + " " + additional_info)

        # Extract damage information
        damage_keywords = self._extract_damage_keywords(title + " " + description)

        return {
            'url': url,
            'source_website': 'schadeautos.nl',
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
            'bmw': 'BMW', 'mercedes': 'Mercedes-Benz', 'mercedes-benz': 'Mercedes-Benz',
            'opel': 'Opel', 'ford': 'Ford', 'renault': 'Renault', 'peugeot': 'Peugeot',
            'citroën': 'Citroën', 'citroen': 'Citroën', 'toyota': 'Toyota',
            'nissan': 'Nissan', 'honda': 'Honda', 'mazda': 'Mazda',
            'hyundai': 'Hyundai', 'kia': 'Kia', 'volvo': 'Volvo',
            'seat': 'SEAT', 'skoda': 'Škoda', 'fiat': 'Fiat',
            'alfa romeo': 'Alfa Romeo', 'mini': 'MINI', 'smart': 'Smart',
            'dacia': 'Dacia', 'suzuki': 'Suzuki', 'mitsubishi': 'Mitsubishi'
        }

        make = None
        for key, value in car_makes.items():
            if key in text:
                make = value
                break

        # Extract year
        year_match = re.search(r'\b(19[8-9][0-9]|20[0-2][0-9])\b', text)
        year = int(year_match.group(1)) if year_match else None

        # Extract mileage (various formats)
        mileage_patterns = [
            r'(\d{1,3}(?:\.\d{3})*)\s*km',
            r'(\d{1,3}(?:,\d{3})*)\s*km',
            r'(\d{1,6})\s*km'
        ]

        mileage = None
        for pattern in mileage_patterns:
            mileage_match = re.search(pattern, text)
            if mileage_match:
                mileage = self.clean_mileage(mileage_match.group(1))
                break

        # Extract model (simplified approach)
        model = None
        if make:
            # Common model extraction patterns
            model_patterns = [
                rf'{make.lower()}\s+([a-z0-9\-\s]+?)(?:\s|$|\d{{4}})',
                rf'{make.lower()}\s+([a-z0-9\-]+)',
            ]

            for pattern in model_patterns:
                model_match = re.search(pattern, text, re.IGNORECASE)
                if model_match:
                    potential_model = model_match.group(1).strip()
                    # Clean and validate model name
                    if 2 <= len(potential_model) <= 15 and not potential_model.isdigit():
                        model = potential_model.title()
                        break

        return make, model, year, mileage

    def _extract_damage_keywords(self, text: str) -> List[str]:
        damage_keywords = [
            # Dutch cosmetic damage terms
            'cosmetische schade', 'lichte schade', 'lakschade', 'deukjes', 'krassen',
            'hagelschade', 'parkeerdeuk', 'kleine schade', 'bumperdeuk', 'krasjes',
            'lakbeschadiging', 'oppervlakkige schade', 'kleine deuk', 'deuken',
            'bumper schade', 'roest', 'verf schade', 'kleine reparatie',

            # English cosmetic damage terms
            'cosmetic damage', 'minor damage', 'paint damage', 'dent', 'scratch',
            'scratches', 'dents', 'minor dent', 'small damage', 'surface damage',
            'bumper damage', 'paint defect', 'rust',

            # General damage terms
            'schade', 'damage', 'beschadigd', 'damaged', 'reparatie', 'repair'
        ]

        found_keywords = []
        text_lower = text.lower()

        for keyword in damage_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords

    def _is_cosmetic_damage_only(self, car: Dict) -> bool:
        # Filter for cosmetic damage only
        severe_keywords = [
            # Dutch severe damage terms
            'motorschade', 'motor defect', 'versnellingsbak schade', 'transmissie schade',
            'frame schade', 'chassis schade', 'water schade', 'brand schade',
            'total loss', 'niet rijdend', 'rijdt niet', 'defect motor',
            'kapotte motor', 'versnellingsbak kapot', 'airbag defect',

            # English severe damage terms
            'engine damage', 'gearbox damage', 'transmission damage',
            'flood damage', 'fire damage', 'structural damage', 'frame damage',
            'total loss', 'not running', 'engine failure', 'airbag deployed',
            'salvage', 'write-off', 'accident damage'
        ]

        text = (car.get('title', '') + " " + car.get('description', '')).lower()

        # Exclude severe damage
        for keyword in severe_keywords:
            if keyword in text:
                return False

        # Look for cosmetic damage indicators
        cosmetic_indicators = [
            'cosmetische', 'lichte', 'lakschade', 'deuk', 'kras', 'bumper',
            'cosmetic', 'minor', 'paint', 'scratch', 'dent', 'surface'
        ]

        has_cosmetic_indicators = any(indicator in text for indicator in cosmetic_indicators)

        # For damage car sites, we're more lenient but still need some indication it's cosmetic
        return has_cosmetic_indicators or len(car.get('damage_keywords', [])) > 0

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
            phone_elements = soup.find_all('a', href=re.compile(r'tel:'))
            phones = [elem.get('href').replace('tel:', '') for elem in phone_elements]
            if phones:
                contact_info['phone'] = phones[0]

            # Email
            email_elements = soup.find_all('a', href=re.compile(r'mailto:'))
            emails = [elem.get('href').replace('mailto:', '') for elem in email_elements]
            if emails:
                contact_info['email'] = emails[0]

            details['contact_info'] = contact_info

            # Additional images
            img_elements = soup.find_all('img')
            images = []
            for img in img_elements:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy')
                if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    if not src.startswith('http'):
                        src = urljoin(car_url, src)
                    images.append(src)

            details['images'] = list(set(images))  # Remove duplicates

            # Extract specifications table
            specs = {}

            # Look for specification tables or lists
            spec_tables = soup.find_all('table')
            for table in spec_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            specs[key] = value

            # Look for dt/dd pairs
            dt_elements = soup.find_all('dt')
            for dt in dt_elements:
                dd = dt.find_next_sibling('dd')
                if dd:
                    key = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    specs[key] = value

            details['specifications'] = specs

            # Extract detailed description
            desc_containers = soup.find_all(['div', 'section'], class_=re.compile(r'description|details|info'))
            full_description = ""
            for container in desc_containers:
                text = container.get_text(strip=True)
                if len(text) > len(full_description):
                    full_description = text

            if full_description:
                details['detailed_description'] = full_description

            return details

        except Exception as e:
            self.logger.error(f"Error scraping car details: {e}")
            return None