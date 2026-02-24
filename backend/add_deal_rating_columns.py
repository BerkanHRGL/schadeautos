#!/usr/bin/env python3
"""
Add deal rating columns to existing cars table
"""
from sqlalchemy.orm import sessionmaker
from database.database import engine
from sqlalchemy import text

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def add_deal_rating_columns():
    session = SessionLocal()

    try:
        # Check if columns exist and add them if they don't
        columns_to_check = ['market_price', 'profit_percentage', 'deal_rating']

        # Get existing columns
        result = session.execute(text("PRAGMA table_info(cars)"))
        existing_columns = [row[1] for row in result.fetchall()]
        print(f"Existing columns: {existing_columns}")

        # Add new columns if they don't exist
        if 'market_price' not in existing_columns:
            print("Adding market_price column")
            session.execute(text("ALTER TABLE cars ADD COLUMN market_price FLOAT"))

        if 'profit_percentage' not in existing_columns:
            print("Adding profit_percentage column")
            session.execute(text("ALTER TABLE cars ADD COLUMN profit_percentage FLOAT"))

        if 'deal_rating' not in existing_columns:
            print("Adding deal_rating column")
            session.execute(text("ALTER TABLE cars ADD COLUMN deal_rating VARCHAR(20)"))

        # Create indexes
        try:
            session.execute(text("CREATE INDEX IF NOT EXISTS ix_cars_profit_percentage ON cars (profit_percentage)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS ix_cars_deal_rating ON cars (deal_rating)"))
        except Exception as e:
            print(f"Index creation warning: {e}")  # Indexes might already exist

        session.commit()
        print("✅ Successfully added deal rating columns")

    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_deal_rating_columns()