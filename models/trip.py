from sqlalchemy import Column, String, Float, DateTime, Boolean
from datetime import datetime
from database import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    driver_id = Column(String, nullable=True)
    status = Column(String)

    pickup_lat = Column(Float)
    pickup_lng = Column(Float)
    drop_lat = Column(Float)
    drop_lng = Column(Float)

    fare = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # OTP fields
    otp = Column(String, nullable=True)
    otp_verified = Column(Boolean, default=False)
    
    # Driver location status
    driver_on_way = Column(Boolean, default=False)
    driver_arrived = Column(Boolean, default=False)
    
    # Rating fields
    user_rated = Column(Boolean, default=False)
    driver_rated = Column(Boolean, default=False)
    
    # Vehicle type selected for this trip
    vehicle_type = Column(String, nullable=True)  # BIKE, AUTO, MINI_CAR, FAMILY_CAR
