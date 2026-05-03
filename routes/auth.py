from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, DriverRegister
from app.services.auth_service import register_user, login_user, register_driver
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/registerUser")
def register(data: UserCreate, db: Session = Depends(get_db)):
    # Standard registration for passengers

    # Check email uniqueness
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Verification for optional driver fields if this route is used for drivers
    if data.vehicle_number and db.query(User).filter(User.vehicle_number == data.vehicle_number).first():
        raise HTTPException(400, "Vehicle number already registered. Each vehicle must be unique.")
    
    if data.dl_number and db.query(User).filter(User.dl_number == data.dl_number).first():
        raise HTTPException(400, "Driving license already registered. Each license must be unique.")

    # Service layer handles hashing and DB insertion
    user = register_user(
        db,
        data.name,
        data.email,
        data.password,
        data.role,
        vehicle_number=data.vehicle_number,
        vehicle_type=data.vehicle_type,
        dl_number=data.dl_number
    )

    return {"id": user.id}

# Dedicated route for Driver registration with mandatory vehicle details
@router.post("/register-driver")
def register_driver_route(data: DriverRegister, db: Session = Depends(get_db)):
    # Dedicated driver registration logic

    # Email check
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")

    # Vehicle number check
    if db.query(User).filter(User.vehicle_number == data.vehicle_number).first():
        raise HTTPException(400, "Vehicle number already registered. Each vehicle must be unique.")

    # DL number check
    if db.query(User).filter(User.dl_number == data.dl_number).first():
        raise HTTPException(400, "Driving license already registered. Each license must be unique.")

    user = register_driver(db, data)

    return {"id": user.id}


# Main login route for all user roles
@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == data.email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Returns a JWT token or similar session identifier
        token = login_user(db, data.email, data.password)

        return {
            "token": token,
            "user_id": user.id,
            "role": user.role
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))