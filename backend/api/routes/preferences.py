from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User, UserPreference
from api.schemas import UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceResponse
from api.routes.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=UserPreferenceResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    preferences = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    if not preferences:
        preferences = UserPreference(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    return preferences

@router.post("/", response_model=UserPreferenceResponse)
async def create_or_update_preferences(
    preferences_data: UserPreferenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing_preferences = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    if existing_preferences:
        for field, value in preferences_data.dict(exclude_unset=True).items():
            setattr(existing_preferences, field, value)
        db.commit()
        db.refresh(existing_preferences)
        return existing_preferences
    else:
        preferences = UserPreference(
            user_id=current_user.id,
            **preferences_data.dict()
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
        return preferences

@router.put("/", response_model=UserPreferenceResponse)
async def update_preferences(
    preferences_data: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    preferences = db.query(UserPreference).filter(
        UserPreference.user_id == current_user.id
    ).first()

    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")

    for field, value in preferences_data.dict(exclude_unset=True).items():
        setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)
    return preferences