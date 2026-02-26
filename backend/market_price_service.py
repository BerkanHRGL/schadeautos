#!/usr/bin/env python3
"""
Market Price Service - Deal calculations and fallback prices
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

        # Fallback prices when median calculation isn't available
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
        """Get fallback market price from static estimates"""
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

        profit_percentage = ((market_price - car_price) / market_price) * 100

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
