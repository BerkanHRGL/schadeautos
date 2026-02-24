from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import datetime

class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, index=True)
    source_website = Column(String(100), index=True)

    # Car details
    make = Column(String(100), index=True)
    model = Column(String(100), index=True)
    year = Column(Integer, index=True)
    mileage = Column(Integer, index=True)
    price = Column(Float, index=True)
    fuel_type = Column(String(50))
    transmission = Column(String(50))
    body_type = Column(String(50))
    color = Column(String(50))

    # Damage information
    damage_description = Column(Text)
    damage_type = Column(String(200))
    damage_keywords = Column(JSON)
    has_cosmetic_damage_only = Column(Boolean, default=True, index=True)

    # Deal analysis
    market_price = Column(Float)  # Market price for comparison
    profit_percentage = Column(Float, index=True)  # How much cheaper than market
    deal_rating = Column(String(20), index=True)  # excellent, good, fair, poor

    # Listing details
    title = Column(String(300))
    description = Column(Text)
    images = Column(JSON)
    contact_info = Column(JSON)
    location = Column(String(200))

    # Metadata
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    notifications = relationship("Notification", back_populates="car")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # Filter preferences
    max_price = Column(Float, default=50000)
    min_price = Column(Float, default=0)
    max_mileage = Column(Integer, default=300000)
    min_year = Column(Integer, default=2000)
    max_year = Column(Integer, default=datetime.datetime.now().year)

    # Car preferences
    preferred_makes = Column(JSON)  # List of car makes
    preferred_models = Column(JSON)  # List of car models
    preferred_fuel_types = Column(JSON)  # List of fuel types
    preferred_body_types = Column(JSON)  # List of body types

    # Damage preferences
    allowed_damage_types = Column(JSON)  # List of allowed damage types
    exclude_severe_damage = Column(Boolean, default=True)

    # Location preferences
    max_distance_km = Column(Integer, default=100)
    preferred_locations = Column(JSON)  # List of preferred locations

    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    notification_frequency = Column(String(20), default="instant")  # instant, daily, weekly

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    car_id = Column(Integer, ForeignKey("cars.id"))

    # Notification details
    notification_type = Column(String(50))  # new_match, price_drop, etc.
    title = Column(String(300))
    message = Column(Text)

    # Status
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")
    car = relationship("Car", back_populates="notifications")

class ScrapingSession(Base):
    __tablename__ = "scraping_sessions"

    id = Column(Integer, primary_key=True, index=True)
    website = Column(String(100), index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Results
    cars_found = Column(Integer, default=0)
    cars_added = Column(Integer, default=0)
    cars_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="running")  # running, completed, failed
    error_message = Column(Text)

    # Metadata
    pages_scraped = Column(Integer, default=0)
    total_requests = Column(Integer, default=0)

class DamageKeyword(Base):
    __tablename__ = "damage_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(200), unique=True, index=True)
    language = Column(String(10), default="nl")  # nl, en
    category = Column(String(50))  # cosmetic, severe, exclude
    weight = Column(Float, default=1.0)  # Weight for scoring

    created_at = Column(DateTime(timezone=True), server_default=func.now())