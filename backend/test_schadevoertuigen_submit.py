#!/usr/bin/env python3
"""
Test submitting the search form on schadevoertuigen.nl
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

def test_form_submission():
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
        # Go to main page first
        print("Going to main page...")
        driver.get("https://www.schadevoertuigen.nl/")
        time.sleep(3)

        # Fill out search form
        print("Filling search form...")

        # Select category - Auto's should already be selected
        try:
            category_select = Select(driver.find_element(By.NAME, "category"))
            category_select.select_by_value("auto")
            print("✅ Category set to auto")
        except Exception as e:
            print(f"❌ Category selection failed: {e}")

        # Select brand - Volkswagen
        try:
            brand_select = Select(driver.find_element(By.NAME, "merk"))
            brand_select.select_by_value("Volkswagen")
            print("✅ Brand set to Volkswagen")
        except Exception as e:
            print(f"❌ Brand selection failed: {e}")

        # Set type - polo
        try:
            type_input = driver.find_element(By.NAME, "search[type]")
            type_input.clear()
            type_input.send_keys("polo")
            print("✅ Type set to polo")
        except Exception as e:
            print(f"❌ Type input failed: {e}")

        # Set fuel type - benzine (should already be selected)
        try:
            fuel_select = Select(driver.find_element(By.NAME, "search[brandstof]"))
            fuel_select.select_by_value("benzine")
            print("✅ Fuel set to benzine")
        except Exception as e:
            print(f"❌ Fuel selection failed: {e}")

        # Set minimum price
        try:
            min_price_input = driver.find_element(By.NAME, "search[min_prijs]")
            min_price_input.clear()
            min_price_input.send_keys("850")
            print("✅ Min price set to 850")
        except Exception as e:
            print(f"❌ Min price input failed: {e}")

        # Submit form
        print("Submitting form...")
        try:
            submit_button = driver.find_element(By.XPATH, "//a[contains(@href, 'document.zoek_voertuig.submit')]")
            submit_button.click()
            print("✅ Form submitted")
        except Exception as e:
            print(f"❌ Submit failed: {e}")
            # Try alternative submit method
            try:
                driver.execute_script("document.zoek_voertuig.submit();")
                print("✅ Form submitted via JavaScript")
            except Exception as e2:
                print(f"❌ JavaScript submit also failed: {e2}")

        # Wait for results
        time.sleep(5)

        print(f"\nAfter submission:")
        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")

        # Look for car listings in results
        page_source = driver.page_source

        # Check for different possible selectors for car listings
        selectors_to_try = [
            "tr[bgcolor]",  # Table rows with background color
            ".vehicle-item",
            ".car-item",
            ".listing-item",
            "tr",
            "table tr",
            "[onclick*='location']"  # Elements with onclick location
        ]

        found_listings = False
        for selector in selectors_to_try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements and len(elements) > 5:  # More than just header rows
                print(f"\nFound {len(elements)} potential listings with selector: {selector}")
                for i, elem in enumerate(elements[:5]):
                    try:
                        text = elem.text.strip()
                        if text and len(text) > 20 and ("polo" in text.lower() or "€" in text):
                            print(f"  Listing {i+1}: {text[:150]}...")
                            found_listings = True
                    except:
                        pass

        if not found_listings:
            print("❌ No car listings found")

            # Look for "no results" message
            if "geen" in page_source.lower() or "niet gevonden" in page_source.lower() or "resultaat" in page_source.lower():
                print("🔍 Possible 'no results' message found")

            # Check if we're still on the search form
            if "zoek_voertuig" in page_source:
                print("🔍 Still on search form page")

            # Save results page for inspection
            with open('/tmp/schadevoertuigen_results.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print("📄 Results page saved to /tmp/schadevoertuigen_results.html")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_form_submission()