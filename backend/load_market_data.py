#!/usr/bin/env python3
"""
Load real market data from your research into the database
"""
from sqlalchemy.orm import sessionmaker
from database.database import engine
from sqlalchemy import text
import logging

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def load_market_data():
    session = SessionLocal()

    # Real market data from your research
    market_data = [
        # Volkswagen Polo
        ("Volkswagen", "polo", 2010, 3900, 10),
        ("Volkswagen", "polo", 2011, 4300, 10),
        ("Volkswagen", "polo", 2012, 4900, 10),
        ("Volkswagen", "polo", 2013, 5700, 10),
        ("Volkswagen", "polo", 2014, 6000, 10),
        ("Volkswagen", "polo", 2015, 6800, 10),
        ("Volkswagen", "polo", 2016, 7200, 10),
        ("Volkswagen", "polo", 2017, 7750, 10),
        ("Volkswagen", "polo", 2018, 8700, 10),
        ("Volkswagen", "polo", 2019, 9800, 10),

        # Volkswagen Golf
        ("Volkswagen", "golf", 2010, 4800, 10),
        ("Volkswagen", "golf", 2011, 5700, 10),
        ("Volkswagen", "golf", 2012, 6400, 10),
        ("Volkswagen", "golf", 2013, 7100, 10),
        ("Volkswagen", "golf", 2014, 7900, 10),
        ("Volkswagen", "golf", 2015, 8800, 10),
        ("Volkswagen", "golf", 2016, 9700, 10),
        ("Volkswagen", "golf", 2017, 10300, 10),
        ("Volkswagen", "golf", 2018, 11000, 10),
        ("Volkswagen", "golf", 2019, 12500, 10),

        # Volkswagen Up
        ("Volkswagen", "up", 2011, 3200, 10),
        ("Volkswagen", "up", 2012, 3900, 10),
        ("Volkswagen", "up", 2013, 4200, 10),
        ("Volkswagen", "up", 2014, 4900, 10),
        ("Volkswagen", "up", 2015, 5600, 10),
        ("Volkswagen", "up", 2016, 5900, 10),
        ("Volkswagen", "up", 2017, 6600, 10),
        ("Volkswagen", "up", 2018, 7000, 10),
        ("Volkswagen", "up", 2019, 7300, 10),
        ("Volkswagen", "up", 2020, 7900, 10),

        # Toyota Yaris
        ("Toyota", "yaris", 2010, 3500, 10),
        ("Toyota", "yaris", 2011, 4700, 10),
        ("Toyota", "yaris", 2012, 5400, 10),
        ("Toyota", "yaris", 2013, 6500, 10),
        ("Toyota", "yaris", 2014, 7200, 10),
        ("Toyota", "yaris", 2015, 8000, 10),
        ("Toyota", "yaris", 2016, 9000, 10),
        ("Toyota", "yaris", 2017, 10500, 10),
        ("Toyota", "yaris", 2018, 12050, 10),
        ("Toyota", "yaris", 2019, 13500, 10),

        # Toyota Aygo
        ("Toyota", "aygo", 2010, 2500, 10),
        ("Toyota", "aygo", 2011, 2900, 10),
        ("Toyota", "aygo", 2012, 3400, 10),
        ("Toyota", "aygo", 2013, 3500, 10),
        ("Toyota", "aygo", 2014, 4200, 10),
        ("Toyota", "aygo", 2015, 5500, 10),
        ("Toyota", "aygo", 2016, 6200, 10),
        ("Toyota", "aygo", 2017, 6500, 10),
        ("Toyota", "aygo", 2018, 7000, 10),
        ("Toyota", "aygo", 2019, 7400, 10),

        # Kia Picanto
        ("Kia", "picanto", 2010, 2000, 10),
        ("Kia", "picanto", 2011, 2800, 10),
        ("Kia", "picanto", 2012, 4000, 10),
        ("Kia", "picanto", 2013, 4000, 10),
        ("Kia", "picanto", 2014, 4400, 10),
        ("Kia", "picanto", 2015, 5500, 10),
        ("Kia", "picanto", 2016, 5800, 10),
        ("Kia", "picanto", 2017, 6700, 10),
        ("Kia", "picanto", 2018, 7000, 10),
        ("Kia", "picanto", 2019, 7800, 10),

        # Fiat 500
        ("Fiat", "500", 2010, 3200, 10),
        ("Fiat", "500", 2011, 3600, 10),
        ("Fiat", "500", 2012, 4000, 10),
        ("Fiat", "500", 2013, 4500, 10),
        ("Fiat", "500", 2014, 4500, 10),
        ("Fiat", "500", 2015, 5600, 10),
        ("Fiat", "500", 2016, 6700, 10),
        ("Fiat", "500", 2017, 7200, 10),
        ("Fiat", "500", 2018, 8200, 10),
        ("Fiat", "500", 2019, 10000, 10),

        # Suzuki Swift
        ("Suzuki", "swift", 2010, 3700, 10),
        ("Suzuki", "swift", 2011, 4500, 10),
        ("Suzuki", "swift", 2012, 5200, 10),
        ("Suzuki", "swift", 2013, 6000, 10),
        ("Suzuki", "swift", 2014, 7000, 10),
        ("Suzuki", "swift", 2015, 7600, 10),
        ("Suzuki", "swift", 2016, 8300, 10),
        ("Suzuki", "swift", 2017, 9800, 10),
        ("Suzuki", "swift", 2018, 10500, 10),
        ("Suzuki", "swift", 2019, 11300, 10),

        # Peugeot 107 (using Toyota Aygo prices as requested)
        ("Peugeot", "107", 2010, 2500, 10),
        ("Peugeot", "107", 2011, 2900, 10),
        ("Peugeot", "107", 2012, 3400, 10),
        ("Peugeot", "107", 2013, 3500, 10),
        ("Peugeot", "107", 2014, 4200, 10),
        ("Peugeot", "107", 2015, 5500, 10),
        ("Peugeot", "107", 2016, 6200, 10),
        ("Peugeot", "107", 2017, 6500, 10),
        ("Peugeot", "107", 2018, 7000, 10),
        ("Peugeot", "107", 2019, 7400, 10),
    ]

    try:
        print("Loading real market data into database...")

        for make, model, year, avg_price, sample_count in market_data:
            # Insert or update market price data
            session.execute(text("""
                INSERT INTO market_prices (make, model, year, average_price, sample_count, last_updated)
                VALUES (:make, :model, :year, :avg_price, :sample_count, CURRENT_TIMESTAMP)
                ON CONFLICT(make, model, year) DO UPDATE SET
                    average_price = :avg_price,
                    sample_count = :sample_count,
                    last_updated = CURRENT_TIMESTAMP
            """), {
                'make': make,
                'model': model,
                'year': year,
                'avg_price': avg_price,
                'sample_count': sample_count
            })

        session.commit()
        print(f"✅ Successfully loaded {len(market_data)} market price entries!")

        # Show summary
        result = session.execute(text("SELECT COUNT(*) FROM market_prices")).fetchone()
        print(f"Total market prices in database: {result[0]}")

    except Exception as e:
        print(f"❌ Error loading market data: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    load_market_data()