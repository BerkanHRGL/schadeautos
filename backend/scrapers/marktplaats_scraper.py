import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from .base_scraper import BaseScraper
import logging

class MarktplaatsScraper(BaseScraper):
    def __init__(self):
        super().__init__(use_selenium=True)
        self.base_url = "https://www.marktplaats.nl"
        # Target specifically the cars section with additional filters
        self.search_url = "https://www.marktplaats.nl/l/auto-s/auto-s/#q:"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        all_cars = []

        for term in search_terms:
            self.logger.info(f"Searching for: {term}")
            search_url = f"{self.search_url}{term.replace(' ', '+')}"

            for page in range(1, max_pages + 1):
                page_url = f"{search_url}|startDateFrom:yesterday|sortBy:SORT_INDEX|sortOrder:DESCENDING"
                if page > 1:
                    page_url += f"|offset:{(page-1)*30}"

                html = await self.get_page(page_url)
                if not html:
                    continue

                cars = self.extract_car_data(html, self.base_url)
                if not cars:
                    break

                all_cars.extend(cars)
                self.logger.info(f"Found {len(cars)} cars on page {page} for term '{term}'")

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
        listings = soup.find_all('article', class_=re.compile(r'hz-Listing'))

        for listing in listings:
            try:
                car = self._extract_single_car(listing, base_url)
                if car and self._has_damage_keywords(car):
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
        title_elem = listing.find('h3') or listing.find('span', class_=re.compile(r'hz-Listing-title'))
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract price
        price_elem = listing.find('span', class_=re.compile(r'hz-Listing-price'))
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        price = self.clean_price(price_text)

        # Extract description
        desc_elem = listing.find('span', class_=re.compile(r'hz-Listing-description'))
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract image
        img_elem = listing.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else None

        # Extract location and date
        location_elem = listing.find('span', class_=re.compile(r'hz-Listing-location'))
        location = location_elem.get_text(strip=True) if location_elem else ""

        # Try to extract car details from title/description
        make, model, year, mileage = self._parse_car_details(title, description)

        return {
            'url': url,
            'source_website': 'marktplaats.nl',
            'title': title,
            'description': description,
            'price': price,
            'make': make,
            'model': model,
            'year': year,
            'mileage': mileage,
            'location': location,
            'images': [image_url] if image_url else [],
            'damage_keywords': self._extract_damage_keywords(title + " " + description),
            'has_cosmetic_damage_only': True
        }

    def _parse_car_details(self, title: str, description: str) -> tuple:
        text = (title + " " + description).lower()

        # Common Dutch car makes
        car_makes = {
            'volkswagen': 'Volkswagen', 'vw': 'Volkswagen', 'audi': 'Audi',
            'bmw': 'BMW', 'mercedes': 'Mercedes-Benz', 'opel': 'Opel',
            'ford': 'Ford', 'renault': 'Renault', 'peugeot': 'Peugeot',
            'citroën': 'Citroën', 'citroen': 'Citroën', 'toyota': 'Toyota',
            'nissan': 'Nissan', 'honda': 'Honda', 'mazda': 'Mazda',
            'hyundai': 'Hyundai', 'kia': 'Kia', 'volvo': 'Volvo',
            'saab': 'Saab', 'seat': 'SEAT', 'skoda': 'Škoda',
            'fiat': 'Fiat', 'alfa romeo': 'Alfa Romeo', 'lancia': 'Lancia'
        }

        make = None
        for key, value in car_makes.items():
            if key in text:
                make = value
                break

        # Extract year (4 digits between 1990-2024)
        year_match = re.search(r'\b(19[9][0-9]|20[0-2][0-9])\b', text)
        year = int(year_match.group(1)) if year_match else None

        # Extract mileage (number followed by km)
        mileage_match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*km', text)
        mileage = self.clean_mileage(mileage_match.group(1)) if mileage_match else None

        # Model is harder to extract reliably, leaving as None for now
        model = None

        return make, model, year, mileage

    def _extract_damage_keywords(self, text: str) -> List[str]:
        damage_keywords = [
            # Dutch cosmetic damage terms
            'cosmetische schade', 'lichte schade', 'lakschade', 'deukjes', 'krassen',
            'hagelschade', 'parkeerdeuk', 'kleine schade', 'bumperdeuk', 'kleine deuk',
            'lakbeschadiging', 'oppervlakkige schade', 'deuken', 'krasjes',

            # English cosmetic damage terms
            'cosmetic damage', 'minor damage', 'paint damage', 'dent', 'scratch',
            'scratches', 'dents', 'minor dent', 'small damage', 'surface damage',

            # General damage terms
            'schade', 'damage', 'beschadigd', 'damaged'
        ]

        found_keywords = []
        text_lower = text.lower()

        for keyword in damage_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords

    def _has_damage_keywords(self, car: Dict) -> bool:
        text = (car.get('title', '') + " " + car.get('description', '')).lower()

        # Temporarily simplified filtering for testing - just exclude obvious non-cars
        non_car_keywords = [
            'onderdeel apart', 'velgen apart', 'motor apart', 'autowrak'
        ]

        # Check if this is an accessory/part listing
        for keyword in non_car_keywords:
            if keyword in text:
                return False

        # Very relaxed damage detection - if it contains any search term, include it
        damage_search_terms = ['schade', 'lakschade', 'deuk', 'kras', 'hagel']
        has_damage_term = any(term in text for term in damage_search_terms)

        # For testing: include if it has damage terms OR if it's in the auto section
        return has_damage_term or 'auto' in text

    async def scrape_car_details(self, car_url: str) -> Optional[Dict]:
        html = await self.get_page(car_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        try:
            # Extract additional details from the full page
            details = {}

            # Phone number
            phone_elem = soup.find('a', href=re.compile(r'tel:'))
            if phone_elem:
                details['phone'] = phone_elem.get('href').replace('tel:', '')

            # Additional images
            img_elements = soup.find_all('img', src=re.compile(r'marktplaats'))
            images = [img.get('src') for img in img_elements if img.get('src')]
            details['images'] = images

            # Detailed description
            desc_container = soup.find('div', class_=re.compile(r'description'))
            if desc_container:
                details['detailed_description'] = desc_container.get_text(strip=True)

            # Car specifications
            spec_elements = soup.find_all('dt')
            specs = {}
            for dt in spec_elements:
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