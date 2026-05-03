from pydantic import BaseModel
from typing import Optional

class RatingCreate(BaseModel):
    trip_id: str
    rater_id: str
    ratee_id: str
    rating_type: str  # "PASSENGER" or "DRIVER"
    score: int  # 1-5
    comment: Optional[str] = None

class RatingResponse(BaseModel):
    id: str
    trip_id: str
    rater_id: str
    ratee_id: str
    rating_type: str
    score: int
    comment: Optional[str]
    created_at: str

    class Config:
        from_attributes = True
