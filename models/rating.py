from sqlalchemy import Column, String, Integer, ForeignKey, Text
from app.database import Base

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id"))
    rater_id = Column(String, ForeignKey("users.id"))
    ratee_id = Column(String, ForeignKey("users.id"))

    score = Column(Integer)
    comment = Column(Text, nullable=True)
