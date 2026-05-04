from sqlalchemy import Column, String, ForeignKey
from database import Base

class DriverProfile(Base):
    __tablename__ = "driver_profiles"

    driver_id = Column(String, ForeignKey("users.id"), primary_key=True)
    vehicle_number = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)
    dl_number = Column(String, nullable=False)
