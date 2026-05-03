from pydantic import BaseModel
from typing import Optional

class RideRequest(BaseModel):
    user_id: str
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    vehicle_type: Optional[str] = None  # BIKE, AUTO, MINI_CAR, FAMILY_CAR - optional for price preview

class RideAccept(BaseModel):
    trip_id: str
    driver_id: str

class TripAction(BaseModel):
    trip_id: str
    user_id: str = None  # Optional, used for cancel to verify ownership

class OTPVerification(BaseModel):
    trip_id: str
    otp: str
    user_id: str

class DriverLocationUpdate(BaseModel):
    trip_id: str
    driver_id: str
    status: str  # "ON_THE_WAY" or "ARRIVED"

class SubmitRating(BaseModel):
    trip_id: str
    rater_id: str
    ratee_id: str
    score: int
    comment: Optional[str] = None
    rating_type: str  # "PASSENGER" or "DRIVER"
