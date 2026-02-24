import asyncio
import aiohttp
import time
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager
import logging

class BaseScraper(ABC):
    def __init__(self, delay_range=(2, 5), use_selenium=True):
        self.delay_range = delay_range
        self.use_selenium = use_selenium
        self.user_agent = UserAgent()
        self.session = None
        self.driver = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def setup(self):
        if self.use_selenium:
            await self._setup_selenium()
        else:
            await self._setup_session()

    async def _setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={self.user_agent.random}")
        # Use system chromium
        chrome_options.binary_location = "/usr/bin/chromium"

        try:
            # Try using system chromedriver first
            self.driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service("/usr/bin/chromedriver"),
                options=chrome_options
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise

    async def _setup_session(self):
        headers = {
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'nl-NL,nl;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        if self.driver:
            self.driver.quit()
        if self.session:
            await self.session.close()

    async def random_delay(self):
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)

    async def get_page(self, url: str) -> str:
        await self.random_delay()

        if self.use_selenium:
            return await self._get_page_selenium(url)
        else:
            return await self._get_page_session(url)

    async def _get_page_selenium(self, url: str) -> str:
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Error getting page with Selenium: {e}")
            return ""

    async def _get_page_session(self, url: str) -> str:
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    self.logger.error(f"HTTP {response.status} for URL: {url}")
                    return ""
        except Exception as e:
            self.logger.error(f"Error getting page with aiohttp: {e}")
            return ""

    @abstractmethod
    async def scrape_search_results(self, search_terms: List[str], max_pages: int = 5) -> List[Dict]:
        pass

    @abstractmethod
    async def scrape_car_details(self, car_url: str) -> Optional[Dict]:
        pass

    @abstractmethod
    def extract_car_data(self, html: str, base_url: str = "") -> List[Dict]:
        pass

    def clean_price(self, price_text: str) -> Optional[float]:
        if not price_text:
            return None

        price_text = price_text.replace("€", "").replace(".", "").replace(",", ".")
        price_text = ''.join(filter(lambda x: x.isdigit() or x == '.', price_text))

        try:
            return float(price_text)
        except ValueError:
            return None

    def clean_mileage(self, mileage_text: str) -> Optional[int]:
        if not mileage_text:
            return None

        mileage_text = mileage_text.replace("km", "").replace(".", "").replace(",", "")
        mileage_text = ''.join(filter(str.isdigit, mileage_text))

        try:
            return int(mileage_text)
        except ValueError:
            return None

    def clean_year(self, year_text: str) -> Optional[int]:
        if not year_text:
            return None

        year_text = ''.join(filter(str.isdigit, year_text))

        try:
            year = int(year_text)
            if 1900 <= year <= 2024:
                return year
            return None
        except ValueError:
            return None