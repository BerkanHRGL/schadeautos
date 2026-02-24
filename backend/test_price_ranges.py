#!/usr/bin/env python3
"""
Test if cars exist in our price range for target models
"""
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def test_price_ranges():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/chromium"

    driver = webdriver.Chrome(
        service=webdriver.chrome.service.Service("/usr/bin/chromedriver"),
        options=chrome_options
    )

    def clean_price(price_text):
        if not price_text:
            return None
        price_text = str(price_text).replace("€", "").replace("EUR", "")
        price_text = re.sub(r'[^\\d.,]', '', price_text)
        if not price_text:
            return None
        if ',' in price_text and '.' in price_text:
            price_text = price_text.replace('.', '').replace(',', '.')
        elif ',' in price_text:
            parts = price_text.split(',')
            if len(parts[-1]) <= 2:
                price_text = price_text.replace(',', '.')
            else:
                price_text = price_text.replace(',', '')
        try:
            return float(price_text)
        except ValueError:
            return None

    try:
        # Test a few models with different price ranges
        test_cases = [
            ("Suzuki Swift", "https://www.marktplaats.nl/l/auto-s/suzuki/#q:suzuki+swift|mileageTo:200001|PriceCentsFrom:150000|PriceCentsTo:700000|constructionYearFrom:2012|constructionYearTo:2025|sortBy:PRICE|sortOrder:INCREASING"),
            ("VW Polo - broader range", "https://www.marktplaats.nl/l/auto-s/volkswagen/#q:volkswagen+polo|mileageTo:200001|PriceCentsFrom:100000|PriceCentsTo:1500000|constructionYearFrom:2012|constructionYearTo:2025|sortBy:PRICE|sortOrder:INCREASING"),
            ("VW Polo - original", "https://www.marktplaats.nl/l/auto-s/volkswagen/#q:volkswagen+polo|mileageTo:200001|PriceCentsFrom:150000|PriceCentsTo:700000|constructionYearFrom:2012|constructionYearTo:2025|sortBy:PRICE|sortOrder:INCREASING")
        ]

        for name, url in test_cases:
            print(f"\\n=== Testing {name} ===")
            driver.get(url)
            time.sleep(3)

            listings = driver.find_elements(By.CSS_SELECTOR, ".hz-Listing")
            print(f"Found {len(listings)} listings")

            prices = []
            for i, listing in enumerate(listings[:5]):
                try:
                    full_text = listing.text
                    print(f"Listing {i+1}: {full_text[:100]}...")

                    price_match = re.search(r'€\s*([\\d.,]+)', full_text)
                    if price_match:
                        price = clean_price(price_match.group())
                        print(f"  Price found: €{price}")
                        if price:
                            prices.append(price)
                    else:
                        print(f"  No price pattern found")
                except Exception as e:
                    print(f"  Error: {e}")

            print(f"Valid prices: {sorted(prices)}")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_price_ranges()