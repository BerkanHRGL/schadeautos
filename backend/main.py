from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse
import uvicorn
from decouple import config
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import or_
from database.database import engine, Base
from database.models import Car, User, UserPreference, Notification, ScrapingSession

# Create all tables on startup
Base.metadata.create_all(bind=engine)
from scraping_service import ScrapingService
from background_scheduler import start_scheduler, stop_scheduler
from typing import List, Optional
from datetime import datetime
import logging
import atexit
from api.routes import auth

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Car Damage Finder API",
    description="API for finding cars with cosmetic damage in the Netherlands",
    version="1.0.0"
)

frontend_url = config("FRONTEND_URL", default="http://localhost:3000")
allowed_origins = [origin.strip() for origin in frontend_url.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])

# Start background scheduler
@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()

# Also register cleanup for direct script execution
atexit.register(stop_scheduler)

@app.get("/dashboard.html")
async def get_dashboard():
    return FileResponse("dashboard.html")

@app.get("/test.html")
async def get_test():
    return FileResponse("test.html")

@app.get("/")
async def root():
    return {"message": "Car Damage Finder API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/cars")
async def get_cars(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    max_mileage: int = Query(None, ge=0),
    search: str = Query(None),
    db = Depends(get_db)
):
    query = db.query(Car).filter(Car.is_active == True)

    # Filter out cars with more than 200,000 km
    query = query.filter(
        or_(Car.mileage == None, Car.mileage <= 200000)
    )

    if min_price is not None:
        query = query.filter(Car.price >= min_price)

    if max_price is not None:
        query = query.filter(Car.price <= max_price)

    if max_mileage is not None:
        query = query.filter(Car.mileage <= max_mileage)

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            Car.title.ilike(search_lower) |
            Car.description.ilike(search_lower) |
            Car.make.ilike(search_lower)
        )

    cars = query.offset(skip).limit(limit).all()

    # Convert to dict format for frontend compatibility
    result = []
    for car in cars:
        result.append({
            "id": car.id,
            "url": car.url,
            "source_website": car.source_website,
            "make": car.make,
            "model": car.model,
            "year": car.year,
            "mileage": car.mileage,
            "price": car.price,
            "title": car.title,
            "description": car.description,
            "damage_keywords": car.damage_keywords or [],
            "has_cosmetic_damage_only": car.has_cosmetic_damage_only,
            "images": car.images or [],
            "first_seen": car.first_seen.isoformat() if car.first_seen else None,
            "is_active": car.is_active,
            "location": car.location,
            "market_price": car.market_price,
            "profit_percentage": car.profit_percentage,
            "deal_rating": car.deal_rating
        })

    return result

@app.get("/api/cars/{car_id}")
async def get_car(car_id: int, db = Depends(get_db)):
    car = db.query(Car).filter(
        Car.id == car_id,
        or_(Car.mileage == None, Car.mileage <= 200000)
    ).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    return {
        "id": car.id,
        "url": car.url,
        "source_website": car.source_website,
        "make": car.make,
        "model": car.model,
        "year": car.year,
        "mileage": car.mileage,
        "price": car.price,
        "title": car.title,
        "description": car.description,
        "damage_keywords": car.damage_keywords or [],
        "has_cosmetic_damage_only": car.has_cosmetic_damage_only,
        "images": car.images or [],
        "first_seen": car.first_seen.isoformat() if car.first_seen else None,
        "is_active": car.is_active,
        "location": car.location,
        "market_price": car.market_price,
        "profit_percentage": car.profit_percentage,
        "deal_rating": car.deal_rating
    }

@app.get("/api/cars/stats/summary")
async def get_car_stats(db = Depends(get_db)):
    cars = db.query(Car).filter(
        Car.is_active == True,
        or_(Car.mileage == None, Car.mileage <= 200000)
    ).all()

    total_cars = len(cars)
    cosmetic_only = len([car for car in cars if car.has_cosmetic_damage_only])
    avg_price = sum(car.price for car in cars if car.price) / len([car for car in cars if car.price]) if cars else 0
    unique_makes = len(set(car.make for car in cars if car.make))

    return {
        "total_cars": total_cars,
        "cosmetic_damage_only": cosmetic_only,
        "average_price": round(avg_price, 2),
        "unique_makes": unique_makes
    }

# Authentication endpoints are now handled by auth.router

# TODO: Implement proper preferences and notifications endpoints

async def _run_scraping_task():
    """Background task to run scraping"""
    try:
        service = ScrapingService()
        result = await service.run_scraping_session()
        logging.getLogger(__name__).info(f"Scraping completed: {result}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Scraping failed: {e}")

@app.post("/api/scraping/run")
async def run_scraping(background_tasks: BackgroundTasks):
    """Manually trigger a scraping session (runs in background)"""
    background_tasks.add_task(_run_scraping_task)
    return {"message": "Scraping started in background. Check /api/scraping/sessions for progress."}

@app.get("/api/scraping/sessions")
async def get_scraping_sessions(db = Depends(get_db)):
    """Get recent scraping sessions"""
    sessions = db.query(ScrapingSession).order_by(ScrapingSession.started_at.desc()).limit(10).all()

    result = []
    for session in sessions:
        result.append({
            "id": session.id,
            "website": session.website,
            "status": session.status,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "cars_found": session.cars_found,
            "cars_added": session.cars_added,
            "cars_updated": session.cars_updated,
            "error_message": session.error_message
        })

    return result

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )