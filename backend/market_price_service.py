#!/usr/bin/env python3
"""
Market Price Service - Live Marktplaats price lookups and deal calculations
"""
import re
import asyncio
import aiohttp
import statistics
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import sessionmaker
from database.database import engine
from sqlalchemy import text
import logging

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class MarketPriceService:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # Cache: (make_lower, model_lower, year) -> median_price
        self._price_cache: Dict[Tuple[str, str, int], Optional[float]] = {}

        # Fallback prices when live lookup fails
        self.fallback_prices = {
            ("Volkswagen", "polo"): 3450,
            ("Volkswagen", "golf"): 3450,
            ("Volkswagen", "up"): 3450,
            ("Toyota", "yaris"): 4500,
            ("Toyota", "aygo"): 4500,
            ("Kia", "picanto"): 2850,
            ("Fiat", "500"): 3000,
            ("Suzuki", "swift"): 2499,
            ("Ford", "fiesta"): 2248,
            ("Renault", "clio"): 1800,
            ("Opel", "corsa"): 1500,
            ("Opel", "astra"): 1500,
            ("Hyundai", "i10"): 2500,
            ("Citroen", "c1"): 2000,
            ("Peugeot", "107"): 2000,
        }

    async def fetch_live_market_price(self, make: str, model: str, year: int) -> Optional[float]:
        """
        Search Marktplaats for undamaged versions of this car to get market price.
        Returns median price from search results, or None if lookup fails.
        """
        cache_key = (make.lower(), model.lower(), year)
        if cache_key in self._price_cache:
            self.logger.debug(f"Cache hit for {make} {model} {year}")
            return self._price_cache[cache_key]

        try:
            prices = await self._search_marktplaats_prices(make, model, year)

            if prices:
                median_price = statistics.median(prices)
                self.logger.info(
                    f"Live market price for {make} {model} {year}: €{median_price:.0f} "
                    f"(median of {len(prices)} results, range €{min(prices):.0f}-€{max(prices):.0f})"
                )
                self._price_cache[cache_key] = median_price
                return median_price
            else:
                self.logger.warning(f"No live prices found for {make} {model} {year}")
                self._price_cache[cache_key] = None
                return None

        except Exception as e:
            self.logger.error(f"Live price lookup failed for {make} {model} {year}: {e}")
            self._price_cache[cache_key] = None
            return None

    async def _search_marktplaats_prices(self, make: str, model: str, year: int) -> List[float]:
        """Search Marktplaats API for undamaged car prices"""
        min_year = year - 1
        max_year = year + 1
        query = f"{make} {model}"

        # Marktplaats search API - category 91 = Vehicles, 72 = Cars
        api_url = "https://www.marktplaats.nl/lrp/api/search"
        params = {
            "l1CategoryId": "91",
            "l2CategoryId": "72",
            "limit": "25",
            "offset": "0",
            "query": query,
            "searchInTitleAndDescription": "true",
            "viewOptions": "list-view",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
            "Referer": "https://www.marktplaats.nl/",
        }

        prices = []

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(api_url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"Marktplaats API returned status {resp.status}")
                        return []

                    data = await resp.json()
                    listings = data.get("listings", [])

                    for listing in listings:
                        try:
                            # Skip "schade" listings - we want undamaged cars
                            title = (listing.get("title") or "").lower()
                            desc = (listing.get("description") or "").lower()
                            combined = f"{title} {desc}"

                            if any(kw in combined for kw in ["schade", "damage", "beschadigd", "total loss", "defect", "kapot", "onderdelen", "parts"]):
                                continue

                            # Extract price
                            price_info = listing.get("priceInfo", {})
                            price_cents = price_info.get("priceCents")
                            if not price_cents:
                                continue
                            price = price_cents / 100.0

                            # Filter: price > €1000 to skip parts/scrap
                            if price < 1000:
                                continue

                            # Filter: reasonable price range (not super expensive outliers)
                            if price > 30000:
                                continue

                            # Filter by year if available in attributes
                            car_year = None
                            attributes = listing.get("attributes", [])
                            for attr in attributes:
                                if attr.get("key") == "constructionYear":
                                    try:
                                        car_year = int(attr.get("value", "0"))
                                    except (ValueError, TypeError):
                                        pass
                                    break

                            # Also try categorySpecificAttributes
                            if not car_year:
                                cat_attrs = listing.get("categorySpecificAttributes", [])
                                for attr in cat_attrs:
                                    if attr.get("key") == "constructionYear":
                                        try:
                                            car_year = int(attr.get("value", "0"))
                                        except (ValueError, TypeError):
                                            pass
                                        break

                            # If we found year, check range
                            if car_year and (car_year < min_year or car_year > max_year):
                                continue

                            prices.append(price)

                        except Exception as e:
                            self.logger.debug(f"Error parsing listing: {e}")
                            continue

        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout searching Marktplaats for {query}")
        except Exception as e:
            self.logger.error(f"Error searching Marktplaats: {e}")

        # Take first 10 valid prices (already filtered)
        return prices[:10]

    def get_market_price(self, make: str, model: str, year: int) -> Optional[float]:
        """Get market price - checks cache first, then falls back to static prices"""
        # Check if we have a cached live price
        cache_key = (make.lower(), model.lower(), year)
        if cache_key in self._price_cache and self._price_cache[cache_key] is not None:
            return self._price_cache[cache_key]

        # Fall back to static estimates
        key = (make, model.lower())
        if key in self.fallback_prices:
            fallback_price = self.fallback_prices[key]
            baseline_year = 2020
            years_diff = baseline_year - year
            adjusted_price = fallback_price * (0.9 ** max(0, years_diff))
            self.logger.debug(f"Using fallback price for {make} {model} {year}: €{adjusted_price:.0f}")
            return adjusted_price

        self.logger.warning(f"No market price found for {make} {model} {year}")
        return None

    def calculate_deal_metrics(self, make: str, model: str, year: int, car_price: float) -> Dict:
        """Calculate deal metrics (profit percentage and rating) for a car"""
        market_price = self.get_market_price(make, model, year)

        if not market_price:
            return {
                'market_price': None,
                'profit_percentage': None,
                'deal_rating': None
            }

        # Calculate profit percentage (how much below market)
        profit_percentage = ((market_price - car_price) / market_price) * 100

        # Determine deal rating
        if profit_percentage >= 50:
            deal_rating = "excellent"
        elif profit_percentage >= 30:
            deal_rating = "good"
        elif profit_percentage >= 15:
            deal_rating = "fair"
        else:
            deal_rating = "poor"

        return {
            'market_price': market_price,
            'profit_percentage': profit_percentage,
            'deal_rating': deal_rating
        }

    def update_car_deal_metrics(self, car_id: int, make: str, model: str, year: int, price: float):
        """Update deal metrics for a specific car in the database"""
        if not year or not price:
            return

        metrics = self.calculate_deal_metrics(make, model, year, price)

        session = SessionLocal()
        try:
            session.execute(text("""
                UPDATE cars
                SET market_price = :market_price,
                    profit_percentage = :profit_percentage,
                    deal_rating = :deal_rating,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = :car_id
            """), {
                'car_id': car_id,
                'market_price': metrics['market_price'],
                'profit_percentage': metrics['profit_percentage'],
                'deal_rating': metrics['deal_rating']
            })

            session.commit()
            if metrics['deal_rating']:
                self.logger.debug(f"Updated deal metrics for car {car_id}: {metrics['deal_rating']} deal")

        except Exception as e:
            self.logger.error(f"Error updating car deal metrics: {e}")
            session.rollback()
        finally:
            session.close()

    async def update_all_car_deal_metrics(self):
        """Update deal metrics for all cars - does live lookups per unique make/model/year"""
        session = SessionLocal()

        try:
            # Get all active cars
            cars = session.execute(text("""
                SELECT id, make, model, year, price
                FROM cars
                WHERE is_active = 1 AND price IS NOT NULL
            """)).fetchall()

            self.logger.info(f"Updating deal metrics for {len(cars)} cars...")

            # Collect unique make/model/year combos for batch lookup
            unique_combos = set()
            for car in cars:
                _, make, model, year, _ = car
                if make and model and year:
                    unique_combos.add((make, model, year))

            # Do live lookups for each unique combo (with delay between requests)
            self.logger.info(f"Looking up live prices for {len(unique_combos)} unique make/model/year combos...")
            for i, (make, model, year) in enumerate(unique_combos):
                try:
                    await self.fetch_live_market_price(make, model, year)
                    # Small delay between API requests to be respectful
                    if i < len(unique_combos) - 1:
                        await asyncio.sleep(1)
                except Exception as e:
                    self.logger.error(f"Live lookup failed for {make} {model} {year}: {e}")

            # Now update all cars using cached prices
            updated_count = 0
            for car in cars:
                car_id, make, model, year, price = car
                if make and model and year and price:
                    self.update_car_deal_metrics(car_id, make, model, year, price)
                    updated_count += 1

            self.logger.info(f"Updated deal metrics for {updated_count} cars")

        except Exception as e:
            self.logger.error(f"Error updating all car deal metrics: {e}")
        finally:
            session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    service = MarketPriceService()
    asyncio.run(service.update_all_car_deal_metrics())
