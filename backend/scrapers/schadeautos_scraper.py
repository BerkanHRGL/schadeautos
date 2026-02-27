import re
import time
import statistics
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
import logging

# Same year range as Marktplaats scraper
MIN_YEAR = 2014
MAX_YEAR = 2019

MAKE_MAP = {
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


class SchadeautosScraper(BaseScraper):
    def __init__(self):
        super().__init__(use_selenium=True)
        self.base_url = "https://www.schadeautos.nl"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        all_cars = []
        seen_urls = set()
        search_count = 0

        for term in search_terms:
            search_count += 1
            self.logger.info(f"[{search_count}] Searching schadeautos.nl: {term}")

            # Restart browser every 10 searches to prevent memory crashes
            if search_count > 1 and search_count % 10 == 0:
                try:
                    await self.restart_browser()
                except Exception as e:
                    self.logger.error(f"Failed to restart browser: {e}")
                    break

            make_slug, model_slug, proper_make, proper_model = self._term_to_parts(term)
            if not make_slug or not model_slug:
                self.logger.warning(f"Could not parse make/model from: {term}")
                continue

            search_url = f"{self.base_url}/nl/schade/personenautos/{make_slug}/{model_slug}"
            self.logger.info(f"URL: {search_url}")

            # Navigate away first to force full reload
            if self.driver:
                try:
                    self.driver.get("about:blank")
                    time.sleep(0.5)
                except Exception:
                    pass

            html = await self.get_page(search_url)
            if not html:
                self.logger.warning(f"No HTML returned for: {term}")
                continue

            # Wait for JS to render listings
            if self.driver:
                try:
                    time.sleep(3)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    html = self.driver.page_source
                except Exception as e:
                    self.logger.error(f"Error during page interaction: {e}")

            # Extract all cars for this make/model
            candidates = self.extract_car_data(html, self.base_url)
            self.logger.info(f"Found {len(candidates)} total listings for '{term}'")

            if not candidates:
                continue

            # Process per year (same range as Marktplaats)
            for year in range(MIN_YEAR, MAX_YEAR + 1):
                year_candidates = [c for c in candidates if c.get('year') == year]
                if not year_candidates:
                    continue

                # Get market price: try Marktplaats DB data first, fall back to service
                market_price = self._get_market_price_from_db(proper_make, proper_model, year)
                if not market_price:
                    market_price = self._get_market_price_from_service(proper_make, proper_model, year)
                if not market_price:
                    self.logger.warning(
                        f"No market price for {proper_make} {proper_model} {year}, skipping"
                    )
                    continue

                threshold = market_price * 0.70  # 30% below market
                self.logger.info(
                    f"Market price for {term} ({year}): €{market_price:.0f}, "
                    f"threshold: €{threshold:.0f}"
                )

                for candidate in year_candidates:
                    url = candidate.get('url')
                    price = candidate.get('price')

                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    if not price or price <= 500:
                        continue

                    if price > threshold:
                        continue

                    profit_percentage = ((market_price - price) / market_price) * 100

                    if profit_percentage >= 50:
                        deal_rating = "excellent"
                    elif profit_percentage >= 30:
                        deal_rating = "good"
                    else:
                        deal_rating = "fair"

                    candidate.update({
                        'make': candidate.get('make') or proper_make,
                        'model': candidate.get('model') or proper_model,
                        'year': year,
                        'market_price': market_price,
                        'profit_percentage': round(profit_percentage, 1),
                        'deal_rating': deal_rating,
                    })

                    self.logger.info(
                        f"Deal: {candidate.get('title', '')[:50]} | "
                        f"€{price:.0f} vs market €{market_price:.0f} ({year}) | "
                        f"{profit_percentage:.0f}% below | {deal_rating}"
                    )
                    all_cars.append(candidate)

        self.logger.info(f"Total below-market cars from SchadeAutos: {len(all_cars)}")
        return all_cars

    def _term_to_parts(self, term: str):
        """Parse a search term like 'volkswagen polo' into URL slugs and proper names."""
        term_lower = term.lower().strip()

        # Check multi-word makes first (e.g. "alfa romeo")
        for key in sorted(MAKE_MAP.keys(), key=len, reverse=True):
            if term_lower.startswith(key + ' '):
                proper_make = MAKE_MAP[key]
                make_slug = key.replace(' ', '-')
                remainder = term_lower[len(key):].strip()
                if remainder:
                    model_slug = remainder.replace(' ', '-')
                    proper_model = remainder.split()[0].title()
                    return make_slug, model_slug, proper_make, proper_model

        # Single-word make: split on first space
        parts = term_lower.split(' ', 1)
        if len(parts) == 2:
            make_slug = parts[0]
            model_slug = parts[1].replace(' ', '-')
            proper_make = MAKE_MAP.get(parts[0], parts[0].title())
            proper_model = parts[1].split()[0].title()
            return make_slug, model_slug, proper_make, proper_model

        return None, None, None, None

    def _get_market_price_from_db(self, make: str, model: str, year: int) -> Optional[float]:
        """Query median market_price from Marktplaats cars already in the DB."""
        try:
            from sqlalchemy.orm import sessionmaker
            from database.database import engine
            from database.models import Car

            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            try:
                rows = (
                    session.query(Car.market_price)
                    .filter(
                        Car.source_website == 'marktplaats.nl',
                        Car.make.ilike(f'%{make}%'),
                        Car.model.ilike(f'%{model}%'),
                        Car.year == year,
                        Car.market_price.isnot(None),
                    )
                    .all()
                )
                prices = [r.market_price for r in rows if r.market_price]
                if len(prices) >= 3:
                    median = statistics.median(prices)
                    self.logger.debug(
                        f"DB market price for {make} {model} {year}: €{median:.0f} "
                        f"(from {len(prices)} Marktplaats listings)"
                    )
                    return median
            finally:
                session.close()
        except Exception as e:
            self.logger.debug(f"DB market price query failed: {e}")
        return None

    def _get_market_price_from_service(self, make: str, model: str, year: int) -> Optional[float]:
        """Fallback: use MarketPriceService static estimates."""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from market_price_service import MarketPriceService
            return MarketPriceService().get_market_price(make, model, year)
        except Exception as e:
            self.logger.debug(f"MarketPriceService lookup failed: {e}")
        return None

    def extract_car_data(self, html: str, base_url: str = "") -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        cars = []

        # SchadeAutos uses <a> tags linking to /nl/schade/personenautos/... with <h2> titles
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

        full_text = link_elem.get_text(separator=' ', strip=True)
        if not full_text or len(full_text) < 5:
            return None

        # Title from <h2>
        title_elem = link_elem.find('h2')
        title = title_elem.get_text(strip=True) if title_elem else full_text.split('€')[0].strip()

        # Price — schadeautos.nl shows two prices: lower "exportprijs" first, then the
        # regular selling price. Take the MAXIMUM to get the actual asking price.
        price = None
        price_matches = re.findall(r'€\s*([\d.,]+)', full_text)
        if price_matches:
            valid_prices = []
            for pm in price_matches:
                p = self._parse_dutch_price(pm)
                if p and p > 100:
                    valid_prices.append(p)
            if valid_prices:
                price = max(valid_prices)

        # Year — first try icon alt texts (e.g. alt="1ste toelating: 2016"),
        # then fall back to a bare 4-digit number in the text.
        year = None
        for img in link_elem.find_all('img'):
            alt = img.get('alt', '')
            if 'toelating' in alt or 'bouwjaar' in alt:
                ym = re.search(r'\b(19[89]\d|20[0-2]\d)\b', alt)
                if ym:
                    year = int(ym.group(1))
                    break
        if not year:
            year_match = re.search(r'\b(19[89]\d|20[0-2]\d)\b', full_text)
            if year_match:
                year = int(year_match.group(1))

        # Mileage — try icon alt texts first (e.g. alt="tellerstand: 125.000 km"),
        # then fall back to text.
        mileage = None
        for img in link_elem.find_all('img'):
            alt = img.get('alt', '')
            if 'tellerstand' in alt:
                mm = re.search(r'([\d.,]+)', alt)
                if mm:
                    mileage_text = mm.group(1).replace('.', '').replace(',', '')
                    try:
                        mileage = int(mileage_text)
                    except ValueError:
                        pass
                break
        if not mileage:
            mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:km|KM)', full_text)
            if mileage_match:
                mileage_text = mileage_match.group(1).replace('.', '').replace(',', '')
                try:
                    mileage = int(mileage_text)
                except ValueError:
                    pass

        # Fuel type — try icon alt texts (e.g. alt="brandstof: benzine"), then text.
        fuel_keywords = {'benzine': 'Benzine', 'diesel': 'Diesel', 'elektrisch': 'Elektrisch',
                         'hybride': 'Hybride', 'lpg': 'LPG'}
        fuel_type = None
        for img in link_elem.find_all('img'):
            alt = img.get('alt', '').lower()
            if 'brandstof' in alt:
                for key, value in fuel_keywords.items():
                    if key in alt:
                        fuel_type = value
                        break
                break
        if not fuel_type:
            text_lower = full_text.lower()
            for key, value in fuel_keywords.items():
                if key in text_lower:
                    fuel_type = value
                    break

        # Image — schadeautos.nl listing links contain multiple <img> tags: small icon
        # images (/gfx/...) and the actual car photo (/cache/picture/...).
        # Find the car photo specifically; fall back to the parent container.
        image_url = None
        search_containers = [link_elem, link_elem.parent] if link_elem.parent else [link_elem]
        for container in search_containers:
            for img in container.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                if '/cache/picture/' in src:
                    image_url = src
                    break
                alt = img.get('alt', '').lower()
                if src and alt.startswith('schadeauto'):
                    image_url = src
                    break
            if image_url:
                break
        if image_url and not image_url.startswith('http'):
            image_url = urljoin(base_url, image_url)

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
        if not price_text:
            return None
        cleaned = price_text.replace('.', '').replace(',', '.')
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_make_model(self, title: str) -> tuple:
        title_lower = title.lower()
        make = None
        model = None

        for key, value in MAKE_MAP.items():
            if title_lower.startswith(key) or f' {key} ' in f' {title_lower} ':
                make = value
                after_make = title_lower.split(key, 1)[1].strip() if key in title_lower else ''
                if after_make:
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
