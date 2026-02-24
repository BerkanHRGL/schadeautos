#!/usr/bin/env python3
"""
Create market prices table for storing year-based market data
"""
from sqlalchemy.orm import sessionmaker
from database.database import engine
from sqlalchemy import text

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_market_prices_table():
    session = SessionLocal()

    try:
        # Create market_prices table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS market_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            make VARCHAR(100) NOT NULL,
            model VARCHAR(100) NOT NULL,
            year INTEGER NOT NULL,
            average_price FLOAT NOT NULL,
            sample_count INTEGER NOT NULL,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(make, model, year)
        )
        """

        session.execute(text(create_table_sql))

        # Create indexes
        session.execute(text("CREATE INDEX IF NOT EXISTS ix_market_prices_make_model_year ON market_prices (make, model, year)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS ix_market_prices_make ON market_prices (make)"))
        session.execute(text("CREATE INDEX IF NOT EXISTS ix_market_prices_year ON market_prices (year)"))

        session.commit()
        print("✅ Successfully created market_prices table")

    except Exception as e:
        print(f"❌ Error creating table: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_market_prices_table()