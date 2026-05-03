from pydantic import BaseModel, EmailStr
from typing import Literal, Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # USER / DRIVER
    # Optional driver fields to prevent 422 errors
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    dl_number: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class DriverRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    vehicle_number: str
    vehicle_type: Literal["BIKE", "AUTO", "MINI_CAR", "FAMILY_CAR"]
    dl_number: str