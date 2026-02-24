#!/usr/bin/env python3
"""
Debug script to see what happens with each listing
"""
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_listings():
    """Debug what happens to each listing"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.binary_location = "/usr/bin/chromium"

    driver = webdriver.Chrome(
        service=webdriver.chrome.service.Service("/usr/bin/chromedriver"),
        options=chrome_options
    )

    try:
        logger.info("Navigating to marktplaats...")
        driver.get("https://www.marktplaats.nl/l/auto-s/?priceFrom=1500&priceTo=5000&query=schade")

        time.sleep(5)

        # Accept cookies if present
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepteren') or contains(text(), 'Accept')]"))
            )
            cookie_button.click()
            logger.info("Accepted cookies")
            time.sleep(2)
        except:
            logger.info("No cookie banner found")

        # Find listings
        listings = driver.find_elements(By.CSS_SELECTOR, ".hz-Listing")
        logger.info(f"Found {len(listings)} total listings")

        valid_cars = 0
        for i, listing in enumerate(listings[:10]):  # Debug first 10
            logger.info(f"\n--- Processing listing {i+1} ---")

            try:
                # Get text
                full_text = listing.text
                logger.info(f"Text length: {len(full_text)}")
                logger.info(f"First 100 chars: {full_text[:100]}...")

                if not full_text or len(full_text) < 10:
                    logger.info("❌ Rejected: Text too short")
                    continue

                # Extract title
                lines = full_text.split('\n')
                title = lines[0] if lines else ""
                logger.info(f"Title: {title}")

                if not title or len(title) < 5:
                    logger.info("❌ Rejected: Title too short")
                    continue

                # Get URL
                try:
                    link_elem = listing.find_element(By.TAG_NAME, "a")
                    url = link_elem.get_attribute("href")
                    if url and not url.startswith("http"):
                        url = urljoin("https://www.marktplaats.nl", url)
                    logger.info(f"URL: {url}")

                    if not url or 'marktplaats.nl' not in url:
                        logger.info("❌ Rejected: Invalid URL")
                        continue
                except:
                    logger.info("❌ Rejected: No URL found")
                    continue

                # Extract price
                price_match = re.search(r'€\s*([\d.,]+)', full_text)
                price = None
                if price_match:
                    price_text = price_match.group().replace("€", "").replace(".", "").replace(",", ".")
                    try:
                        price = float(price_text)
                        logger.info(f"Price: €{price}")
                        if price > 10000:  # 2x max_price
                            logger.info("❌ Rejected: Price too high")
                            continue
                    except:
                        logger.info("Price parsing failed")
                else:
                    logger.info("No price found (will accept)")

                logger.info("✅ Valid car found!")
                valid_cars += 1

                if valid_cars >= 5:  # Stop after finding 5 valid cars
                    break

            except Exception as e:
                logger.error(f"Error processing listing {i+1}: {e}")

        logger.info(f"\nSummary: {valid_cars} valid cars out of {min(10, len(listings))} listings processed")

    finally:
        driver.quit()

if __name__ == "__main__":
    debug_listings()