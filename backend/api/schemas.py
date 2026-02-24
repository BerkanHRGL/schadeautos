from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

class CarBase(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    price: Optional[float] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    color: Optional[str] = None
    damage_description: Optional[str] = None
    damage_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

class CarCreate(CarBase):
    url: str
    source_website: str
    damage_keywords: Optional[List[str]] = []
    images: Optional[List[str]] = []
    contact_info: Optional[Dict[str, Any]] = {}

class CarResponse(CarBase):
    id: int
    url: str
    source_website: str
    damage_keywords: Optional[List[str]] = []
    has_cosmetic_damage_only: bool
    images: Optional[List[str]] = []
    contact_info: Optional[Dict[str, Any]] = {}
    market_price: Optional[float] = None
    profit_percentage: Optional[float] = None
    deal_rating: Optional[str] = None
    first_seen: datetime
    last_updated: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

class CarFilter(BaseModel):
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    max_mileage: Optional[int] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    makes: Optional[List[str]] = []
    models: Optional[List[str]] = []
    fuel_types: Optional[List[str]] = []
    body_types: Optional[List[str]] = []
    damage_types: Optional[List[str]] = []
    locations: Optional[List[str]] = []
    cosmetic_only: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserPreferenceBase(BaseModel):
    max_price: float = 50000
    min_price: float = 0
    max_mileage: int = 300000
    min_year: int = 2000
    max_year: int = 2024
    preferred_makes: Optional[List[str]] = []
    preferred_models: Optional[List[str]] = []
    preferred_fuel_types: Optional[List[str]] = []
    preferred_body_types: Optional[List[str]] = []
    allowed_damage_types: Optional[List[str]] = []
    exclude_severe_damage: bool = True
    max_distance_km: int = 100
    preferred_locations: Optional[List[str]] = []
    email_notifications: bool = True
    notification_frequency: str = "instant"

class UserPreferenceCreate(UserPreferenceBase):
    pass

class UserPreferenceUpdate(UserPreferenceBase):
    pass

class UserPreferenceResponse(UserPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationBase(BaseModel):
    notification_type: str
    title: str
    message: str

class NotificationCreate(NotificationBase):
    user_id: int
    car_id: Optional[int] = None

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    car_id: Optional[int] = None
    is_read: bool
    is_sent: bool
    sent_at: Optional[datetime] = None
    created_at: datetime
    car: Optional[CarResponse] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ScrapingStats(BaseModel):
    total_sessions: int
    successful_sessions: int
    failed_sessions: int
    last_scrape: Optional[datetime] = None
    cars_added_today: int
    cars_updated_today: int