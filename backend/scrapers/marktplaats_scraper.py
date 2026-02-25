import re
import time
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base_scraper import BaseScraper
import logging

# Damage keywords that indicate fixable cosmetic damage (what we WANT)
GOOD_DAMAGE_KEYWORDS = [
    # Dutch - side damage (zijschade)
    'zijschade', 'zij schade', 'zijkant schade', 'zijkant beschadigd',
    'beide zijkanten', 'zijkanten',
    # Dutch - cosmetic/light damage
    'cosmetische schade', 'lichte schade', 'kleine schade',
    'lakschade', 'lakbeschadiging', 'verf schade',
    # Dutch - dents
    'deuk', 'deukje', 'deukjes', 'deuken', 'parkeerdeuk', 'bumperdeuk',
    # Dutch - scratches
    'kras', 'krassen', 'krasje', 'krasjes', 'bekrast',
    # Dutch - bumper
    'bumper schade', 'bumper beschadigd', 'bumperschade',
    # Dutch - hail
    'hagelschade', 'hagel schade',
    # Dutch - panel/body damage
    'plaatwerk schade', 'plaatwerkschade', 'carrosserie schade',
    # Dutch - general repairable
    'aanrijding', 'aanrijdingsschade',
    # Dutch - general schade
    'schade', 'beschadigd', 'beschadigde',
    # English equivalents
    'side damage', 'cosmetic damage', 'minor damage', 'paint damage',
    'dent', 'scratch', 'bumper damage', 'hail damage', 'body damage',
]

# Severe damage - exact phrases that clearly indicate technical/unfixable damage
SEVERE_DAMAGE_KEYWORDS = [
    # Dutch - engine/mechanical (specific phrases only)
    'motorschade', 'motor defect', 'motor kapot', 'kapotte motor',
    'motor is kapot', 'motor tikt', 'motor rammelt',
    'versnellingsbak defect', 'versnellingsbak kapot',
    'koppeling defect', 'koppeling kapot',
    'turbo defect', 'turbo kapot',
    # Dutch - structural
    'frame schade', 'chassis schade', 'constructie schade',
    # Dutch - water/fire
    'water schade', 'waterschade', 'brand schade', 'brandschade',
    'ondergelopen',
    # Dutch - total loss
    'total loss', 'totaal verlies', 'total-loss',
    # Dutch - not drivable
    'niet rijdend', 'rijdt niet', 'niet rijdbaar', 'start niet',
    'spring niet aan',
    # Dutch - airbag specific (not just "airbag" alone)
    'airbag afgegaan', 'airbag defect', 'airbag deployed', 'airbag eruit',
    'airbags afgegaan', 'airbag geactiveerd',
    # Dutch - wreck
    'autowrak', 'sloop', 'sloopauto',
    # English equivalents
    'engine damage', 'engine failure', 'gearbox damage',
    'flood damage', 'fire damage', 'structural damage', 'frame damage',
    'total loss', 'write-off', 'salvage', 'not running',
]

# Technical problems that indicate the car is NOT just cosmetic damage
# These are checked with context (surrounding words matter)
TECHNICAL_PROBLEM_PHRASES = [
    # Motor problems
    'motor loopt niet', 'motor slaat niet aan', 'motor maakt geluid',
    'motor rookt', 'olie lekt', 'koelvloeistof lekt',
    # Gearbox problems
    'schakelt niet', 'schakelproblemen', 'bak kraakt',
    # Electrical
    'elektrisch defect', 'storing motor', 'startmotor defect',
    # Overheating
    'oververhit', 'kop defect', 'cilinderkop',
]


def analyze_damage_text(text: str) -> dict:
    """
    Analyze car description to determine if damage is cosmetic or technical.
    Returns: {'is_cosmetic': bool, 'reason': str, 'damage_types': list}
    """
    text_lower = text.lower()

    # Check for severe/technical damage first
    for keyword in SEVERE_DAMAGE_KEYWORDS:
        if keyword in text_lower:
            return {
                'is_cosmetic': False,
                'reason': f'Severe damage: {keyword}',
                'damage_types': [keyword]
            }

    for phrase in TECHNICAL_PROBLEM_PHRASES:
        if phrase in text_lower:
            return {
                'is_cosmetic': False,
                'reason': f'Technical problem: {phrase}',
                'damage_types': [phrase]
            }

    # Check for positive cosmetic damage indicators
    cosmetic_found = []
    for kw in GOOD_DAMAGE_KEYWORDS:
        if kw in text_lower:
            cosmetic_found.append(kw)

    # Check context clues that suggest car drives fine
    positive_signs = [
        'technisch in orde', 'technisch goed', 'rijdt prima', 'rijdt goed',
        'mechanisch in orde', 'mechanisch goed', 'loopt goed', 'loopt prima',
        'motor loopt goed', 'motor is goed', 'geen technische',
        'alleen cosmetisch', 'alleen optisch', 'alleen uiterlijk',
        'schade is alleen', 'verder in goede staat',
        'apk', 'nieuwe apk',  # has valid inspection
    ]

    has_positive = any(sign in text_lower for sign in positive_signs)

    if cosmetic_found:
        return {
            'is_cosmetic': True,
            'reason': 'Cosmetic damage found' + (' + drives well' if has_positive else ''),
            'damage_types': cosmetic_found
        }

    return {
        'is_cosmetic': False,
        'reason': 'No damage keywords found',
        'damage_types': []
    }


class MarktplaatsScraper(BaseScraper):
    def __init__(self):
        super().__init__(use_selenium=True)
        self.base_url = "https://www.marktplaats.nl"

    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 3) -> List[Dict]:
        all_cars = []
        # Track URLs already seen to skip duplicates early
        seen_urls = set()
        consecutive_crashes = 0

        for i, term in enumerate(search_terms):
            self.logger.info(f"[{i+1}/{len(search_terms)}] Searching Marktplaats for: {term}")

            # Restart browser every 5 searches to prevent memory crashes
            if i > 0 and i % 5 == 0:
                try:
                    await self.restart_browser()
                    consecutive_crashes = 0
                except Exception as e:
                    self.logger.error(f"Failed to restart browser: {e}")
                    break

            search_url = (
                f"{self.base_url}/l/auto-s/"
                f"#q:{term.replace(' ', '+')}"
                f"|PriceCentsTo:600000"
                f"|mileageTo:200001"
                f"|constructionYearFrom:2014"
            )

            html = await self.get_page(search_url)
            if not html:
                self.logger.warning(f"No HTML returned for term: {term}")
                consecutive_crashes += 1
                # If 3 crashes in a row, restart browser
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

            # Step 1: Extract car URLs and basic info from search results
            candidates = self._extract_car_urls(html, self.base_url)
            self.logger.info(f"Found {len(candidates)} car listings for term '{term}'")

            # Step 2: Visit each car page to read the FULL description
            for candidate in candidates:
                # Skip if already processed this URL
                if candidate['url'] in seen_urls:
                    continue
                seen_urls.add(candidate['url'])

                try:
                    car = await self._fetch_full_car_details(candidate, term)
                    if car:
                        all_cars.append(car)
                except Exception as e:
                    self.logger.error(f"Error fetching car details: {e}")
                    continue

        # Remove duplicates based on URL
        seen_urls = set()
        unique_cars = []
        for car in all_cars:
            if car.get('url') and car['url'] not in seen_urls:
                seen_urls.add(car['url'])
                unique_cars.append(car)

        self.logger.info(f"Total unique damage cars from Marktplaats: {len(unique_cars)}")
        return unique_cars

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

    async def _fetch_full_car_details(self, candidate: Dict, search_term: str) -> Optional[Dict]:
        """Visit the individual car page and read the FULL description"""
        url = candidate['url']
        self.logger.info(f"Fetching full details: {candidate['title'][:50]}")

        html = await self.get_page(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Extract the FULL description from the car page
        full_description = ''

        # Try various selectors for the description
        desc_selectors = [
            ('div', {'class': re.compile(r'description|Description')}),
            ('section', {'class': re.compile(r'description|Description')}),
            ('div', {'id': re.compile(r'description|Description')}),
            ('div', {'class': re.compile(r'listing-description|ListingDescription')}),
        ]

        for tag, attrs in desc_selectors:
            desc_elem = soup.find(tag, attrs)
            if desc_elem:
                full_description = desc_elem.get_text(separator=' ', strip=True)
                break

        # Fallback: get all paragraph text
        if not full_description:
            paragraphs = soup.find_all('p')
            texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30]
            full_description = ' '.join(texts)

        # Combine title + full description for damage analysis
        combined_text = f"{candidate['title']} {full_description}"

        self.logger.info(f"Full description length: {len(full_description)} chars")

        # Use smart damage analysis
        analysis = analyze_damage_text(combined_text)

        if not analysis['is_cosmetic']:
            self.logger.info(f"Excluded ({analysis['reason']}): {candidate['title'][:50]}")
            return None

        damage_keywords = analysis['damage_types']
        self.logger.info(f"✅ Including: {candidate['title'][:50]} | damage: {damage_keywords[:3]} | {analysis['reason']}")

        # Parse car details from full text
        make, model, year, mileage = self._parse_car_details(combined_text)

        # Extract all images from the car page
        images = []
        if candidate.get('image_url'):
            images.append(candidate['image_url'])
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src and 'marktplaats' in src and src not in images:
                images.append(src)

        return {
            'url': url,
            'source_website': 'marktplaats.nl',
            'title': candidate['title'],
            'description': full_description[:2000],
            'price': candidate.get('price'),
            'make': make,
            'model': model,
            'year': year,
            'mileage': mileage,
            'location': candidate.get('location', ''),
            'images': images,
            'damage_keywords': damage_keywords,
            'has_cosmetic_damage_only': True,
        }

    def _parse_car_details(self, text: str) -> tuple:
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
        for key, value in car_makes.items():
            if key in text_lower:
                make = value
                break

        year_match = re.search(r'\b(20[0-2]\d|19[89]\d)\b', text)
        year = int(year_match.group(1)) if year_match else None

        mileage = None
        mileage_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*)\s*km', text_lower)
        if mileage_match:
            mileage = self.clean_mileage(mileage_match.group(1))

        model = None
        return make, model, year, mileage

    # Keep the abstract method signature compatible
    def extract_car_data(self, html: str, base_url: str = "") -> List[Dict]:
        """Not used directly - scrape_search_results handles everything"""
        return []

    async def scrape_car_details(self, car_url: str) -> Optional[Dict]:
        """Not used - details are fetched during scrape_search_results"""
        return None
