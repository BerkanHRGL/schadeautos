from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from database.database import get_db
from database.models import Car
from api.schemas import CarResponse, CarFilter
import logging

router = APIRouter()

@router.get("/", response_model=List[CarResponse])
async def get_cars(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    max_mileage: Optional[int] = Query(None, ge=0),
    min_year: Optional[int] = Query(None, ge=1900),
    max_year: Optional[int] = Query(None, le=2024),
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    cosmetic_only: bool = Query(True),
    search: Optional[str] = Query(None),
    sort_by: str = Query("first_seen", regex="^(first_seen|price|mileage|year)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    query = db.query(Car).filter(Car.is_active == True)

    if cosmetic_only:
        query = query.filter(Car.has_cosmetic_damage_only == True)

    if min_price is not None:
        query = query.filter(Car.price >= min_price)

    if max_price is not None:
        query = query.filter(Car.price <= max_price)

    if max_mileage is not None:
        query = query.filter(Car.mileage <= max_mileage)

    if min_year is not None:
        query = query.filter(Car.year >= min_year)

    if max_year is not None:
        query = query.filter(Car.year <= max_year)

    if make:
        query = query.filter(Car.make.ilike(f"%{make}%"))

    if model:
        query = query.filter(Car.model.ilike(f"%{model}%"))

    if search:
        search_filter = or_(
            Car.make.ilike(f"%{search}%"),
            Car.model.ilike(f"%{search}%"),
            Car.title.ilike(f"%{search}%"),
            Car.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    # Sorting
    if sort_order == "desc":
        query = query.order_by(getattr(Car, sort_by).desc())
    else:
        query = query.order_by(getattr(Car, sort_by).asc())

    cars = query.offset(skip).limit(limit).all()

    return cars

@router.get("/{car_id}", response_model=CarResponse)
async def get_car(car_id: int, db: Session = Depends(get_db)):
    car = db.query(Car).filter(Car.id == car_id, Car.is_active == True).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car

@router.get("/stats/summary")
async def get_car_stats(db: Session = Depends(get_db)):
    total_cars = db.query(Car).filter(Car.is_active == True).count()
    cosmetic_only = db.query(Car).filter(
        and_(Car.is_active == True, Car.has_cosmetic_damage_only == True)
    ).count()

    avg_price = db.query(Car).filter(Car.is_active == True).with_entities(
        db.func.avg(Car.price)
    ).scalar() or 0

    makes = db.query(Car.make).filter(Car.is_active == True).distinct().count()

    return {
        "total_cars": total_cars,
        "cosmetic_damage_only": cosmetic_only,
        "average_price": round(avg_price, 2),
        "unique_makes": makes
    }