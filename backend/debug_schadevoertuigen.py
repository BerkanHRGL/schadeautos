#!/usr/bin/env python3
"""
Debug schadevoertuigen.nl page structure to find correct selectors
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def debug_schadevoertuigen():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/chromium"

    driver = webdriver.Chrome(
        service=webdriver.chrome.service.Service("/usr/bin/chromedriver"),
        options=chrome_options
    )

    try:
        # Test the VW Polo URL
        url = "https://www.schadevoertuigen.nl/index.php?page=1&category=auto&merk=Volkswagen&search%5Btype%5D=polo&search%5Btransmission%5D=&search%5Bbouwjaar%5D=&search%5Bbrandstof%5D=benzine&search%5Bprijs%5D=&search%5Bmin_prijs%5D=850&search%5Bmax_prijs%5D="

        print(f"Testing URL: {url}")
        driver.get(url)
        time.sleep(5)

        # Get page source to analyze structure
        page_source = driver.page_source
        print(f"Page title: {driver.title}")
        print(f"Page source length: {len(page_source)}")

        # Try different selectors
        selectors_to_try = [
            ".vehicle-item",
            ".car-item",
            ".listing-item",
            ".vehicle",
            "article",
            ".product-item",
            ".item",
            ".result",
            ".car",
            ".listing",
            "tr",  # table rows
            ".row",
            "[class*='vehicle']",
            "[class*='car']",
            "[class*='item']"
        ]

        for selector in selectors_to_try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"\nFound {len(elements)} elements with selector: {selector}")
                for i, elem in enumerate(elements[:3]):
                    try:
                        text = elem.text.strip()
                        if text and len(text) > 20:  # Only show meaningful content
                            print(f"  Element {i+1}: {text[:100]}...")
                    except:
                        pass

        # Check for specific car-related text
        if "polo" in page_source.lower():
            print(f"\n✅ Page contains 'polo' text")
        else:
            print(f"\n❌ Page does not contain 'polo' text")

        # Look for price patterns
        import re
        prices = re.findall(r'€\s*[\d.,]+', page_source)
        if prices:
            print(f"\nFound prices in page: {prices[:5]}")
        else:
            print(f"\nNo prices found in page")

        # Save page source for analysis
        with open('/tmp/schadevoertuigen_debug.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f"\nPage source saved to /tmp/schadevoertuigen_debug.html")

    finally:
        driver.quit()

if __name__ == "__main__":
    debug_schadevoertuigen()