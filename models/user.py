from sqlalchemy import Column, Integer, String, Boolean, Float
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)  # USER / DRIVER
    is_available = Column(Boolean, default=True)
    rating = Column(Float, default=5.0)  # Average rating
    total_ratings = Column(Integer, default=0)  # Number of ratings received
    
    # Driver-specific fields
    vehicle_number = Column(String,unique=True, nullable=True)
    vehicle_type = Column(String, nullable=True)  # BIKE, AUTO, MINI_CAR, FAMILY_CAR
    dl_number = Column(String,unique=True, nullable=True)