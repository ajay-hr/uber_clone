from sqlalchemy.orm import Session
from app.models.user import User
from app.models.driver_profile import DriverProfile
from app.utils.jwt import create_token
from passlib.context import CryptContext
from app.utils.id_generator import generate_id

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _truncate_password(password):
    password_bytes = password.encode('utf-8')[:72]
    return password_bytes.decode('utf-8', errors='ignore')


def register_user(db: Session, name, email, password, role, vehicle_number=None, vehicle_type=None, dl_number=None):
    password = _truncate_password(password)
    
    # Extra safety check for drivers
    if role == "DRIVER" and not (vehicle_number and dl_number):
        raise ValueError("Drivers must provide vehicle and license details")

    user = User(
        id=generate_id(),
        name=name,
        email=email,
        password=pwd_context.hash(password),
        role=role,
        is_available=True,
        vehicle_number=vehicle_number,
        vehicle_type=vehicle_type,
        dl_number=dl_number
    )

    db.add(user)
    db.commit()
    return user


def register_driver(db: Session, data):
    user = register_user(
        db,
        data.name,
        data.email,
        data.password,
        role="DRIVER",
        vehicle_number=data.vehicle_number,
        vehicle_type=data.vehicle_type,
        dl_number=data.dl_number
    )

    driver_profile = DriverProfile(
        driver_id=user.id,
        vehicle_number=data.vehicle_number,
        vehicle_type=data.vehicle_type,
        dl_number=data.dl_number
    )

    db.add(driver_profile)
    db.commit()

    return user


def login_user(db: Session, email, password):
    password = _truncate_password(password)

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise ValueError("User not found")

    if not pwd_context.verify(password, user.password):
        raise ValueError("Invalid password")

    return create_token({"user_id": user.id, "role": user.role})