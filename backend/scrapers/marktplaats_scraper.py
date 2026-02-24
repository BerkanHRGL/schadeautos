import re
import time
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
import logging


class MarktplaatsScraper(BaseScraper):
    def __init__(self):
        super().__init__(use_selenium=True)
        self.base_url = "https://www.marktplaats.nl"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 3) -> List[Dict]:
        all_cars = []

        for term in search_terms:
            self.logger.info(f"Searching Marktplaats for: {term}")

            # Use the URL format that works with filters
            # f:10882 = filter for "beschadigd" (damaged)
            search_url = (
                f"{self.base_url}/l/auto-s/"
                f"#q:{term.replace(' ', '+')}"
                f"|PriceCentsTo:1500000"
                f"|mileageTo:200001"
                f"|constructionYearFrom:2010"
            )

            html = await self.get_page(search_url)
            if not html:
                self.logger.warning(f"No HTML returned for term: {term}")
                continue

            # Wait for JS to render listings
            if self.driver:
                try:
                    time.sleep(3)  # Wait for dynamic content
                    # Scroll to load more
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    html = self.driver.page_source
                except Exception as e:
                    self.logger.error(f"Error during page interaction: {e}")

            cars = self.extract_car_data(html, self.base_url)
            if cars:
                all_cars.extend(cars)
                self.logger.info(f"Found {len(cars)} cars for term '{term}'")
            else:
                self.logger.warning(f"No cars found for term '{term}'")

        # Remove duplicates based on URL
        seen_urls = set()
        unique_cars = []
        for car in all_cars:
            if car.get('url') and car['url'] not in seen_urls:
                seen_urls.add(car['url'])
                unique_cars.append(car)

        self.logger.info(f"Total unique cars from Marktplaats: {len(unique_cars)}")
        return unique_cars

    def extract_car_data(self, html: str, base_url: str = "") -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        cars = []

        # Try multiple selectors - Marktplaats changes their HTML frequently
        listings = (
            soup.find_all('article', class_=re.compile(r'hz-Listing|Listing')) or
            soup.find_all('li', class_=re.compile(r'hz-Listing|Listing')) or
            soup.find_all('div', class_=re.compile(r'hz-Listing|Listing')) or
            soup.find_all('a', href=re.compile(r'/v/auto-s/'))
        )

        self.logger.info(f"Found {len(listings)} listing elements in HTML")

        # If no listings found with classes, try finding links to car pages
        if not listings:
            listings = soup.find_all('a', href=re.compile(r'/v/auto-s/.+/a\d+'))
            self.logger.info(f"Fallback: found {len(listings)} car links")

        for listing in listings:
            try:
                car = self._extract_single_car(listing, base_url)
                if car and car.get('title') and car.get('url'):
                    cars.append(car)
            except Exception as e:
                self.logger.error(f"Error extracting car data: {e}")
                continue

        return cars

    def _extract_single_car(self, listing, base_url: str) -> Optional[Dict]:
        # Extract URL
        if listing.name == 'a':
            url = urljoin(base_url, listing.get('href', ''))
        else:
            link_elem = listing.find('a', href=True)
            if not link_elem:
                return None
            url = urljoin(base_url, link_elem['href'])

        # Skip non-car URLs
        if '/v/auto-s/' not in url and '/l/auto-s/' not in url:
            return None

        full_text = listing.get_text(separator=' ', strip=True)

        # Extract title - try various selectors
        title = ''
        for selector in ['h3', 'h2', 'h4']:
            title_elem = listing.find(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break

        if not title:
            # Try class-based selectors
            title_elem = listing.find(class_=re.compile(r'title|Title|name|Name'))
            if title_elem:
                title = title_elem.get_text(strip=True)

        if not title:
            return None

        # Extract price
        price = None
        price_elem = listing.find(class_=re.compile(r'price|Price|prijs'))
        if price_elem:
            price = self.clean_price(price_elem.get_text(strip=True))
        else:
            price_match = re.search(r'€\s*([\d.,]+)', full_text)
            if price_match:
                price = self.clean_price(price_match.group(0))

        # Extract description
        desc_elem = listing.find(class_=re.compile(r'description|Description|desc'))
        description = desc_elem.get_text(strip=True) if desc_elem else ''

        # Extract image
        img_elem = listing.find('img')
        image_url = None
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src')

        # Extract location
        location_elem = listing.find(class_=re.compile(r'location|Location'))
        location = location_elem.get_text(strip=True) if location_elem else ''

        # Parse car details
        combined_text = f"{title} {description} {full_text}"
        make, model, year, mileage = self._parse_car_details(combined_text)

        # Extract damage keywords
        damage_keywords = self._extract_damage_keywords(combined_text)

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
            'damage_keywords': damage_keywords,
            'has_cosmetic_damage_only': True,
        }

    def _parse_car_details(self, text: str) -> tuple:
        text_lower = text.lower()

        # Car makes
        car_makes = {
            'volkswagen': 'Volkswagen', 'vw': 'Volkswagen', 'audi': 'Audi',
            'bmw': 'BMW', 'mercedes': 'Mercedes-Benz', 'opel': 'Opel',
            'ford': 'Ford', 'renault': 'Renault', 'peugeot': 'Peugeot',
            'citroën': 'Citroën', 'citroen': 'Citroën', 'toyota': 'Toyota',
            'nissan': 'Nissan', 'honda': 'Honda', 'mazda': 'Mazda',
            'hyundai': 'Hyundai', 'kia': 'Kia', 'volvo': 'Volvo',
            'seat': 'SEAT', 'skoda': 'Škoda', 'fiat': 'Fiat',
            'alfa romeo': 'Alfa Romeo', 'mini': 'MINI', 'smart': 'Smart',
            'dacia': 'Dacia', 'suzuki': 'Suzuki', 'mitsubishi': 'Mitsubishi',
            'porsche': 'Porsche', 'tesla': 'Tesla',
        }

        make = None
        for key, value in car_makes.items():
            if key in text_lower:
                make = value
                break

        # Extract year
        year_match = re.search(r'\b(20[0-2]\d|19[89]\d)\b', text)
        year = int(year_match.group(1)) if year_match else None

        # Extract mileage
        mileage = None
        mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*km', text_lower)
        if mileage_match:
            mileage = self.clean_mileage(mileage_match.group(1))

        model = None
        return make, model, year, mileage

    def _extract_damage_keywords(self, text: str) -> List[str]:
        damage_keywords = [
            'cosmetische schade', 'lichte schade', 'lakschade', 'deukjes', 'krassen',
            'hagelschade', 'parkeerdeuk', 'kleine schade', 'bumperdeuk', 'krasjes',
            'schade', 'beschadigd', 'damaged', 'deuken',
        ]

        found = []
        text_lower = text.lower()
        for kw in damage_keywords:
            if kw in text_lower:
                found.append(kw)
        return found

    async def scrape_car_details(self, car_url: str) -> Optional[Dict]:
        html = await self.get_page(car_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        try:
            details = {}
            img_elements = soup.find_all('img', src=re.compile(r'marktplaats'))
            images = [img.get('src') for img in img_elements if img.get('src')]
            details['images'] = images
            return details
        except Exception as e:
            self.logger.error(f"Error scraping car details: {e}")
            return None
