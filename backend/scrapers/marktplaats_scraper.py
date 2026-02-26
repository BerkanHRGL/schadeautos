import re
import time
import statistics
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
import logging

# Year range to search
MIN_YEAR = 2014
MAX_YEAR = datetime.now().year


class MarktplaatsScraper(BaseScraper):
    def __init__(self):
        super().__init__(use_selenium=True)
        self.base_url = "https://www.marktplaats.nl"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 3) -> List[Dict]:
        all_cars = []
        seen_urls = set()
        consecutive_crashes = 0
        search_count = 0

        for term in search_terms:
            for year in range(MIN_YEAR, MAX_YEAR + 1):
                search_count += 1
                self.logger.info(f"[{search_count}] Searching: {term} ({year})")

                # Restart browser every 10 searches to prevent memory crashes
                if search_count > 1 and search_count % 10 == 0:
                    try:
                        await self.restart_browser()
                        consecutive_crashes = 0
                    except Exception as e:
                        self.logger.error(f"Failed to restart browser: {e}")
                        break

                search_url = (
                    f"{self.base_url}/l/auto-s/"
                    f"#q:{term.replace(' ', '+')}"
                    f"|constructionYearFrom:{year}"
                    f"|constructionYearTo:{year}"
                    f"|mileageTo:180001"
                )

                html = await self.get_page(search_url)
                if not html:
                    self.logger.warning(f"No HTML returned for: {term} ({year})")
                    consecutive_crashes += 1
                    if consecutive_crashes >= 3:
                        self.logger.warning("3 consecutive crashes, restarting browser...")
                        try:
                            await self.restart_browser()
                            consecutive_crashes = 0
                        except Exception as e:
                            self.logger.error(f"Failed to restart browser: {e}")
                            break
                    continue

                consecutive_crashes = 0

                # Wait for JS to render listings
                if self.driver:
                    try:
                        time.sleep(3)
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        html = self.driver.page_source
                    except Exception as e:
                        self.logger.error(f"Error during page interaction: {e}")

                # Extract all car listings from search results
                candidates = self._extract_car_urls(html, self.base_url)
                self.logger.info(f"Found {len(candidates)} listings for '{term}' ({year})")

                # Collect valid prices (> €500) for median calculation
                valid_prices = [c['price'] for c in candidates if c.get('price') and c['price'] > 500]

                if len(valid_prices) < 3:
                    self.logger.warning(f"Not enough prices ({len(valid_prices)}) for '{term}' ({year}), skipping")
                    continue

                median_price = statistics.median(valid_prices)
                threshold = median_price * 0.70  # 30% below median
                self.logger.info(f"Median for '{term}' ({year}): €{median_price:.0f}, threshold: €{threshold:.0f}")

                # Only keep cars priced ≥30% below median
                for candidate in candidates:
                    url = candidate.get('url')
                    price = candidate.get('price')

                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    if not price or price <= 500:
                        continue

                    if price > threshold:
                        continue

                    profit_percentage = ((median_price - price) / median_price) * 100

                    if profit_percentage >= 50:
                        deal_rating = "excellent"
                    elif profit_percentage >= 30:
                        deal_rating = "good"
                    else:
                        deal_rating = "fair"

                    make, model_name, parsed_year, mileage = self._parse_car_details(
                        candidate.get('title', ''), term
                    )

                    images = []
                    if candidate.get('image_url'):
                        images.append(candidate['image_url'])

                    car = {
                        'url': url,
                        'source_website': 'marktplaats.nl',
                        'title': candidate.get('title', ''),
                        'description': '',
                        'price': price,
                        'make': make,
                        'model': model_name,
                        'year': parsed_year or year,
                        'mileage': mileage,
                        'location': candidate.get('location', ''),
                        'images': images,
                        'damage_keywords': [],
                        'has_cosmetic_damage_only': True,
                        'market_price': median_price,
                        'profit_percentage': round(profit_percentage, 1),
                        'deal_rating': deal_rating,
                    }

                    self.logger.info(
                        f"Deal: {candidate.get('title', '')[:50]} | "
                        f"€{price:.0f} vs median €{median_price:.0f} ({year}) | "
                        f"{profit_percentage:.0f}% below | {deal_rating}"
                    )
                    all_cars.append(car)

        self.logger.info(f"Total below-market cars from Marktplaats: {len(all_cars)}")
        return all_cars

    def _extract_car_urls(self, html: str, base_url: str) -> List[Dict]:
        """Extract car URLs and basic info from search results page"""
        soup = BeautifulSoup(html, 'html.parser')
        candidates = []

        # Try multiple selectors
        listings = (
            soup.find_all('article', class_=re.compile(r'hz-Listing|Listing')) or
            soup.find_all('li', class_=re.compile(r'hz-Listing|Listing')) or
            soup.find_all('div', class_=re.compile(r'hz-Listing|Listing')) or
            soup.find_all('a', href=re.compile(r'/v/auto-s/'))
        )

        if not listings:
            listings = soup.find_all('a', href=re.compile(r'/v/auto-s/.+/a\d+'))

        for listing in listings:
            try:
                # Get URL
                if listing.name == 'a':
                    url = urljoin(base_url, listing.get('href', ''))
                else:
                    link_elem = listing.find('a', href=True)
                    if not link_elem:
                        continue
                    url = urljoin(base_url, link_elem['href'])

                if '/v/auto-s/' not in url:
                    continue

                # Get title from search preview
                title = ''
                for selector in ['h3', 'h2', 'h4']:
                    title_elem = listing.find(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                if not title:
                    title_elem = listing.find(class_=re.compile(r'title|Title|name|Name'))
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                if not title:
                    continue

                # Get preview image
                img_elem = listing.find('img')
                image_url = None
                if img_elem:
                    image_url = img_elem.get('src') or img_elem.get('data-src')

                # Get price from preview
                price = None
                price_elem = listing.find(class_=re.compile(r'price|Price|prijs'))
                if price_elem:
                    price = self.clean_price(price_elem.get_text(strip=True))
                else:
                    full_text = listing.get_text(separator=' ', strip=True)
                    price_match = re.search(r'€\s*([\d.,]+)', full_text)
                    if price_match:
                        price = self.clean_price(price_match.group(0))

                # Get location from preview
                location_elem = listing.find(class_=re.compile(r'location|Location'))
                location = location_elem.get_text(strip=True) if location_elem else ''

                candidates.append({
                    'url': url,
                    'title': title,
                    'price': price,
                    'image_url': image_url,
                    'location': location,
                })

            except Exception as e:
                self.logger.error(f"Error extracting car URL: {e}")
                continue

        return candidates

    def _parse_car_details(self, text: str, search_term: str = '') -> tuple:
        text_lower = text.lower()

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
        make_key_found = None
        for key, value in car_makes.items():
            if key in text_lower:
                make = value
                make_key_found = key
                break

        year_match = re.search(r'\b(20[0-2]\d|19[89]\d)\b', text)
        year = int(year_match.group(1)) if year_match else None

        mileage = None
        mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*km', text_lower)
        if mileage_match:
            mileage = self.clean_mileage(mileage_match.group(1))

        # Extract model from text (word after make name)
        model = None
        if make_key_found:
            after_make = text_lower.split(make_key_found, 1)[1].strip()
            if after_make:
                model_match = re.match(r'^([a-z0-9\-]+)', after_make)
                if model_match:
                    candidate = model_match.group(1)
                    if candidate not in ('schade', 'met', 'auto', 'te', 'koop', 'de', 'met'):
                        model = candidate.title()

        # Fallback: extract model from search term
        if not model and search_term:
            term_lower = search_term.lower()
            for key in car_makes:
                if term_lower.startswith(key):
                    remainder = term_lower[len(key):].strip()
                    if remainder:
                        model = remainder.split()[0].title()
                    break

        return make, model, year, mileage

    # Keep the abstract method signature compatible
    def extract_car_data(self, html: str, base_url: str = "") -> List[Dict]:
        """Not used directly - scrape_search_results handles everything"""
        return []

    async def scrape_car_details(self, car_url: str) -> Optional[Dict]:
        """Not used - details are fetched during scrape_search_results"""
        return None
