#!/usr/bin/env python3
"""
Debug price extraction step by step
"""
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def debug_price_extraction():
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
        print(f"    Input price_text: '{price_text}'")

        if not price_text:
            print("    Result: None (empty)")
            return None

        price_text = str(price_text).replace("€", "").replace("EUR", "")
        print(f"    After removing €: '{price_text}'")

        price_text = re.sub(r'[^\d.,]', '', price_text)
        print(f"    After regex cleanup: '{price_text}'")

        if not price_text:
            print("    Result: None (empty after cleanup)")
            return None

        # Handle Dutch number format
        if ',' in price_text and '.' in price_text:
            price_text = price_text.replace('.', '').replace(',', '.')
            print(f"    Dutch format (both , and .): '{price_text}'")
        elif ',' in price_text:
            parts = price_text.split(',')
            if len(parts[-1]) <= 2:
                price_text = price_text.replace(',', '.')
                print(f"    Comma as decimal: '{price_text}'")
            else:
                price_text = price_text.replace(',', '')
                print(f"    Comma as thousands: '{price_text}'")

        try:
            result = float(price_text)
            print(f"    Final result: {result}")
            return result
        except ValueError as e:
            print(f"    ValueError: {e}")
            return None

    try:
        # Test with VW Polo
        url = "https://www.marktplaats.nl/l/auto-s/volkswagen/#q:volkswagen+polo|mileageTo:200001|PriceCentsFrom:150000|PriceCentsTo:700000|constructionYearFrom:2012|constructionYearTo:2025|sortBy:PRICE|sortOrder:INCREASING"

        print(f"Testing URL: {url}")
        driver.get(url)
        time.sleep(5)

        listings = driver.find_elements(By.CSS_SELECTOR, ".hz-Listing")
        print(f"Found {len(listings)} listings")

        prices_found = []

        for i, listing in enumerate(listings[:3]):  # Test first 3
            print(f"\\n=== Listing {i+1} ===")

            try:
                full_text = listing.text
                print(f"Full text: {full_text[:200]}...")

                # Test different regex patterns
                patterns = [
                    r'€\s*([0-9.,]+)',
                    r'€([0-9.,]+)',
                    r'€\s*([\d.,]+)',
                    r'€([\d.,]+)',
                    r'€\s*(\d+[.,]?\d*)',
                ]

                for j, pattern in enumerate(patterns):
                    match = re.search(pattern, full_text)
                    print(f"  Pattern {j+1} ({pattern}): {match.group() if match else 'No match'}")

                # Use the working pattern
                price_match = re.search(r'€\s*([0-9.,]+)', full_text)
                if price_match:
                    price_text = price_match.group()
                    print(f"  Raw price match: '{price_text}'")

                    price = clean_price(price_text)

                    if price and 1500 <= price <= 7000:
                        prices_found.append(price)
                        print(f"  ✅ Valid price in range: €{price}")
                    else:
                        print(f"  ❌ Price €{price} outside range 1500-7000")
                else:
                    print("  No price pattern matched")

            except Exception as e:
                print(f"  Error: {e}")

        print(f"\\nSUMMARY: Found {len(prices_found)} valid prices: {prices_found}")

    finally:
        driver.quit()

if __name__ == "__main__":
    debug_price_extraction()