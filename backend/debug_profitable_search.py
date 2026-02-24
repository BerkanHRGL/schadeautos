#!/usr/bin/env python3
"""
Debug the profitable car search URLs
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def debug_search():
    # Setup Chrome
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
        # Test the URL format we're using
        test_url = "https://www.marktplaats.nl/l/auto-s/volkswagen/#q:volkswagen+polo|mileageTo:200001|PriceCentsFrom:150000|PriceCentsTo:700000|constructionYearFrom:2012|constructionYearTo:2025|sortBy:PRICE|sortOrder:INCREASING"

        print(f"Testing URL: {test_url}")
        driver.get(test_url)
        time.sleep(5)

        # Check for listings
        listings = driver.find_elements(By.CSS_SELECTOR, ".hz-Listing")
        print(f"Found {len(listings)} listings with .hz-Listing selector")

        # Try alternative selectors
        alt_selectors = [
            "[data-listing-id]",
            "article[class*='listing']",
            ".mp-listing",
            ".listing"
        ]

        for selector in alt_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"Found {len(elements)} elements with selector: {selector}")

        # Check page content
        page_text = driver.page_source[:1000]
        print(f"Page starts with: {page_text}")

        # Check if there's a "no results" message
        no_results_indicators = [
            "geen advertenties",
            "no results",
            "0 advertenties",
            "geen resultaten"
        ]

        page_text_lower = driver.page_source.lower()
        for indicator in no_results_indicators:
            if indicator in page_text_lower:
                print(f"Found 'no results' indicator: {indicator}")

        # Let's try a simpler URL format like the user's example
        simple_url = "https://www.marktplaats.nl/l/auto-s/suzuki/#q:suzuki+swift|mileageTo:200001|PriceCentsFrom:150000|PriceCentsTo:700000|constructionYearFrom:2012|constructionYearTo:2025|sortBy:PRICE|sortOrder:INCREASING"

        print(f"\nTesting simpler URL: {simple_url}")
        driver.get(simple_url)
        time.sleep(5)

        listings = driver.find_elements(By.CSS_SELECTOR, ".hz-Listing")
        print(f"Found {len(listings)} listings with simple URL")

    finally:
        driver.quit()

if __name__ == "__main__":
    debug_search()