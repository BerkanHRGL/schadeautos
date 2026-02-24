#!/usr/bin/env python3
"""
Market Price Service - Handles year-specific market price lookups and deal calculations
"""
from typing import Optional, Dict
from sqlalchemy.orm import sessionmaker
from database.database import engine
from sqlalchemy import text
import logging

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class MarketPriceService:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # Fallback prices (original estimates) if no market data available
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

    def get_market_price(self, make: str, model: str, year: int) -> Optional[float]:
        """Get market price for specific make/model/year combination"""
        session = SessionLocal()

        try:
            # First try to get exact match from database
            result = session.execute(text("""
                SELECT average_price, sample_count
                FROM market_prices
                WHERE LOWER(make) = LOWER(:make)
                AND LOWER(model) = LOWER(:model)
                AND year = :year
            """), {
                'make': make,
                'model': model,
                'year': year
            }).fetchone()

            if result and result[1] >= 3:  # Minimum 3 samples for reliability
                self.logger.debug(f"Found market price for {make} {model} {year}: €{result[0]} (from {result[1]} samples)")
                return float(result[0])

            # Try to find price for nearby years (±2 years)
            for year_offset in [1, -1, 2, -2]:
                nearby_year = year + year_offset
                result = session.execute(text("""
                    SELECT average_price, sample_count
                    FROM market_prices
                    WHERE LOWER(make) = LOWER(:make)
                    AND LOWER(model) = LOWER(:model)
                    AND year = :year
                """), {
                    'make': make,
                    'model': model,
                    'year': nearby_year
                }).fetchone()

                if result and result[1] >= 3:
                    # Adjust price for year difference (depreciation ~10% per year)
                    base_price = float(result[0])
                    adjusted_price = base_price * (0.9 ** abs(year_offset))
                    self.logger.debug(f"Found nearby market price for {make} {model} {year}: €{adjusted_price:.0f} (adjusted from {nearby_year})")
                    return adjusted_price

            # Try to get average for this make/model across all years
            result = session.execute(text("""
                SELECT AVG(average_price) as avg_price, COUNT(*) as count_years
                FROM market_prices
                WHERE LOWER(make) = LOWER(:make)
                AND LOWER(model) = LOWER(:model)
            """), {
                'make': make,
                'model': model
            }).fetchone()

            if result and result[0] and result[1] >= 2:  # At least 2 years of data
                avg_price = float(result[0])
                # Apply age depreciation (assuming 2015 as baseline)
                baseline_year = 2015
                years_diff = baseline_year - year
                adjusted_price = avg_price * (0.9 ** max(0, years_diff))
                self.logger.debug(f"Found average market price for {make} {model}: €{adjusted_price:.0f} (age-adjusted)")
                return adjusted_price

            # Fall back to original estimates
            key = (make, model.lower())
            if key in self.fallback_prices:
                fallback_price = self.fallback_prices[key]
                # Apply age depreciation to fallback price too
                baseline_year = 2015
                years_diff = baseline_year - year
                adjusted_price = fallback_price * (0.9 ** max(0, years_diff))
                self.logger.debug(f"Using fallback price for {make} {model} {year}: €{adjusted_price:.0f}")
                return adjusted_price

            self.logger.warning(f"No market price found for {make} {model} {year}")
            return None

        except Exception as e:
            self.logger.error(f"Error getting market price: {e}")
            return None
        finally:
            session.close()

    def calculate_deal_metrics(self, make: str, model: str, year: int, car_price: float) -> Dict:
        """Calculate deal metrics (profit percentage and rating) for a car"""
        market_price = self.get_market_price(make, model, year)

        if not market_price:
            return {
                'market_price': None,
                'profit_percentage': None,
                'deal_rating': None
            }

        # Calculate profit percentage
        profit_percentage = ((market_price - car_price) / market_price) * 100

        # Determine deal rating
        if profit_percentage >= 60:
            deal_rating = "excellent"
        elif profit_percentage >= 40:
            deal_rating = "good"
        elif profit_percentage >= 25:
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
            self.logger.debug(f"Updated deal metrics for car {car_id}: {metrics['deal_rating']} deal")

        except Exception as e:
            self.logger.error(f"Error updating car deal metrics: {e}")
            session.rollback()
        finally:
            session.close()

    def update_all_car_deal_metrics(self):
        """Update deal metrics for all cars in the database"""
        session = SessionLocal()

        try:
            # Get all active cars
            cars = session.execute(text("""
                SELECT id, make, model, year, price
                FROM cars
                WHERE is_active = 1 AND price IS NOT NULL
            """)).fetchall()

            self.logger.info(f"Updating deal metrics for {len(cars)} cars...")

            updated_count = 0
            for car in cars:
                car_id, make, model, year, price = car

                if make and model and year and price:
                    self.update_car_deal_metrics(car_id, make, model, year, price)
                    updated_count += 1

            self.logger.info(f"✅ Updated deal metrics for {updated_count} cars")

        except Exception as e:
            self.logger.error(f"Error updating all car deal metrics: {e}")
        finally:
            session.close()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    service = MarketPriceService()
    service.update_all_car_deal_metrics()