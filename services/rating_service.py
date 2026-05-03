from sqlalchemy.orm import Session
from app.models.rating import Rating
from app.models.user import User
from app.utils.id_generator import generate_id
from sqlalchemy import func

def create_rating(db: Session, trip_id: str, rater_id: str, ratee_id: str, rating_type: str, score: int, comment: str = None):

    # ❗ Prevent duplicate rating
    existing = db.query(Rating).filter(
        Rating.trip_id == trip_id,
        Rating.rater_id == rater_id
    ).first()

    if existing:
        raise ValueError("You have already rated this trip")

    rating = Rating(
        id=generate_id(),
        trip_id=trip_id,
        rater_id=rater_id,
        ratee_id=ratee_id,
        rating_type=rating_type,
        score=score,
        comment=comment
    )

    db.add(rating)
    db.commit()

    update_user_rating(db, ratee_id)

    return rating

def update_user_rating(db: Session, user_id: str):
    """Update user's average rating"""
    ratings = db.query(Rating).filter(Rating.ratee_id == user_id).all()
    
    if ratings:
        avg_rating = sum(r.score for r in ratings) / len(ratings)
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.rating = round(avg_rating, 2)
            user.total_ratings = len(ratings)
            db.commit()

def get_user_ratings(db: Session, user_id: str):
    """Get all ratings for a user"""
    return db.query(Rating).filter(Rating.ratee_id == user_id).all()

def get_rating_for_trip(db: Session, trip_id: str):
    """Get rating for a specific trip"""
    return db.query(Rating).filter(Rating.trip_id == trip_id).first()
