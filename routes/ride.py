from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import get_db
from models.trip import Trip
from models.user import User
from models.rating import Rating
from schemas.trip import RideRequest, RideAccept, TripAction, OTPVerification, DriverLocationUpdate, SubmitRating
from services.matching_service import acquire_lock, release_lock
from services.pricing_service import calculate_fare, get_all_vehicle_prices
from services.rating_service import get_user_ratings
from services.otp_service import generate_otp, verify_otp
from workers.tasks import match_driver_task
from utils.id_generator import generate_id
from datetime import datetime, timezone
import logging
from typing import Optional
from app.websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Real-time updates via WebSocket for trip status and notifications
@router.websocket("/ws/{role}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, role: str, user_id: str):
    await manager.connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"{role} {user_id} disconnected")
    finally:
        manager.disconnect(user_id, websocket)

# Endpoint to preview fares for different vehicle types based on distance
@router.post("/estimate")
def get_ride_estimate(data: RideRequest, db: Session = Depends(get_db)):
    logger.info(f"Price estimate requested from user: {data.user_id}")
    
    # Get prices for all vehicle types
    prices = get_all_vehicle_prices(
        data.pickup_lat,
        data.pickup_lng,
        data.drop_lat,
        data.drop_lng
    )
    
    return {
        "user_id": data.user_id,
        "pickup": {"lat": data.pickup_lat, "lng": data.pickup_lng},
        "dropoff": {"lat": data.drop_lat, "lng": data.drop_lng},
        "vehicle_types": prices
    }

# Create a new trip request and trigger the driver matching process
@router.post("/request")
async def request_ride(data: RideRequest, db: Session = Depends(get_db)):

    # Prevent a user from having multiple concurrent active trips
    existing_trip = db.query(Trip).filter(
        Trip.user_id == data.user_id,
        Trip.status.in_(["REQUESTED", "DRIVER_ASSIGNED", "ONGOING"])
    ).first()

    if existing_trip:
        raise HTTPException(
            status_code=400,
            detail="You already have an active trip. Cancel it before booking another."
        )

    vehicle_type = data.vehicle_type or "BIKE"

    # Initialize trip in the database
    trip = Trip(
        id=generate_id(),
        user_id=data.user_id,
        pickup_lat=data.pickup_lat,
        pickup_lng=data.pickup_lng,
        drop_lat=data.drop_lat,
        drop_lng=data.drop_lng,
        status="REQUESTED",
        vehicle_type=vehicle_type
    )

    db.add(trip)
    db.commit()

    # Offload driver searching to a background task (Celery)
    match_driver_task.delay(
        data.pickup_lat,
        data.pickup_lng,
        vehicle_type,
        trip.id
    )

    return {
        "trip_id": trip.id,
        "vehicle_type": vehicle_type
    }

# Endpoint for drivers to claim a pending ride request
@router.post("/accept")
async def accept_ride(data: RideAccept, db: Session = Depends(get_db)):
    logger.info(f"Driver {data.driver_id} attempting to accept trip {data.trip_id}")
    lock_key = f"trip_lock:{data.trip_id}"

    # Distributed lock ensures only one driver can accept the same trip simultaneously
    if not acquire_lock(lock_key):
        raise HTTPException(status_code=400, detail="Ride already taken")

    try:
        trip = db.query(Trip).filter(Trip.id == data.trip_id).first()

        if not trip:
            raise HTTPException(status_code=400, detail="Trip not found")
        
        # Ensure trip hasn't been cancelled by user while driver was deciding
        if trip.status == "CANCELLED":
            raise HTTPException(status_code=400, detail="This trip has been cancelled")

        if trip.status != "REQUESTED":
            raise HTTPException(status_code=400, detail="Invalid trip")

        # Check if driver is trying to accept their own ride
        if trip.user_id == data.driver_id:
            raise HTTPException(status_code=400, detail="Cannot accept your own ride")

        driver = db.query(User).filter(User.id == data.driver_id).first()

        if not driver:
            logger.error(f"Driver acceptance failed: Driver {data.driver_id} not found in database")
            raise HTTPException(status_code=404, detail="Driver not found. Please check the driver ID.")
            
        # Basic driver state validation
        if not driver.is_available:
            raise HTTPException(status_code=400, detail="Driver is currently busy or offline")

        # Verify driver role
        if driver.role != "DRIVER":
            raise HTTPException(status_code=400, detail="Only drivers can accept rides")

        # Verify vehicle type matches requested type
        if driver.vehicle_type != trip.vehicle_type:
            raise HTTPException(status_code=400, 
                                detail=f"Vehicle mismatch: This trip requires a {trip.vehicle_type}, but you have a {driver.vehicle_type}")

        # Update driver and trip status to reserved
        driver.is_available = False

        trip.driver_id = data.driver_id
        trip.status = "DRIVER_ASSIGNED"

        db.commit()

        # Security: Generate OTP that passenger must give to driver
        otp = generate_otp(data.trip_id)
        trip.otp = otp
        db.commit()

        logger.info(f"Trip {data.trip_id} successfully assigned to driver {data.driver_id}")
        logger.info(f"OTP {otp} generated for trip {data.trip_id}, sending to user {trip.user_id}")
        
        # Real-time alert to passenger with driver details and OTP
        await manager.send(
            trip.user_id,
            {
                "type": "OTP_GENERATED",
                "trip_id": trip.id,
                "driver_id": trip.driver_id,
                "driver_name": driver.name,
                "otp": otp,
                "message": f"🚕 {driver.name} accepted your ride! OTP: {otp}",
                "driver_vehicle_number": driver.vehicle_number,
                "driver_rating": driver.rating or 0,
            }
        )
        
        return {
            "message": "Ride accepted! Driver is on the way.",
            "trip_id": trip.id,
            "driver_id": trip.driver_id,
            "user_id": trip.user_id
        }

    finally:
        release_lock(lock_key)

# Mark the ride as started once the passenger is inside the vehicle
@router.post("/start")
async def start_trip(data: TripAction, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.status != "DRIVER_ASSIGNED":
        raise HTTPException(status_code=400, detail=f"Cannot start trip in status {trip.status}")

    # Start is forbidden until verify-otp endpoint has been called successfully
    if not trip.otp_verified:
        raise HTTPException(status_code=400, detail="OTP must be verified before starting the trip")

    # Only the driver who accepted the ride can start it
    if data.user_id and trip.driver_id != data.user_id:
        raise HTTPException(status_code=403, detail="Only the assigned driver can start the trip")

    trip.status = "ONGOING"
    db.commit()

    # Notify both parties that the ride is now active
    await manager.send_to_many(
        [trip.user_id, trip.driver_id],
        {
            "type": "TRIP_STARTED",
            "trip_id": trip.id,
            "message": "Trip has started"
        }
    )

    logger.info(f"Trip {data.trip_id} started")
    return {"message": "Trip started"}

# Finalize trip, calculate total fare, and release driver
@router.post("/end")
async def end_trip(data: TripAction, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
        
    if trip.status != "ONGOING":
        raise HTTPException(status_code=400, detail=f"Cannot end trip in status {trip.status}")

    # Only the assigned driver is authorized to end the ride
    if data.user_id and trip.driver_id != data.user_id:
        raise HTTPException(status_code=403, detail="Only the assigned driver can end the trip")
        
    # Use the vehicle_type stored in the trip, default to BIKE if not set
    vehicle_type = trip.vehicle_type or "BIKE"

    # Pricing logic based on GPS coordinates and vehicle tier
    fare = calculate_fare(
        trip.pickup_lat,
        trip.pickup_lng,
        trip.drop_lat,
        trip.drop_lng,
        vehicle_type
    )

    trip.status = "COMPLETED"
    trip.completed_at = datetime.now(timezone.utc)
    trip.fare = fare

    # Make driver available for new matches again
    driver = db.query(User).filter(User.id == trip.driver_id).first()
    if driver:
        driver.is_available = True
        logger.info(f"Driver {driver.id} is now available again")

    db.commit()
    
    logger.info(f"Trip {data.trip_id} ended with fare: {fare} for vehicle type: {vehicle_type}")

    await manager.send_to_many(
        [trip.user_id, trip.driver_id],
        {
            "type": "TRIP_COMPLETED",
            "trip_id": trip.id,
            "fare": fare,
            "vehicle_type": vehicle_type
        }
    )

    return {"fare": fare, "vehicle_type": vehicle_type}

# Allow user to cancel before the ride begins
@router.post("/cancel")
def cancel_ride(data: TripAction, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Only the user who requested the trip can cancel it
    if trip.user_id != data.user_id:
        raise HTTPException(status_code=403, detail="Only the trip requester can cancel this trip")

    # Only allow cancel before driver accepts
    if trip.status not in ["REQUESTED", "DRIVER_ASSIGNED"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel this trip"
        )
    trip.status = "CANCELLED"
    db.commit()

    return {"message": "Trip cancelled"}


# Retrieve all ratings received by a specific user (displayed in Step 2)
@router.get("/ratings/{user_id}")
def get_user_all_ratings(user_id: str, db: Session = Depends(get_db)):
    logger.info(f"Fetching ratings for user {user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        ratings = get_user_ratings(db, user_id)
        return {
            "user_id": user_id,
            "average_rating": getattr(user, 'rating', 0.0) or 0.0,
            "total_ratings": getattr(user, 'total_ratings', 0) or 0,
            "ratings": [
                {
                    "id": getattr(r, 'id', None),
                    "trip_id": getattr(r, 'trip_id', None),
                    "score": getattr(r, 'score', 0),
                    "comment": getattr(r, 'comment', ""),
                    "rater_id": getattr(r, 'rater_id', None),
                    "created_at": (
                        r.created_at.isoformat() if hasattr(r, 'created_at') and r.created_at and hasattr(r.created_at, 'isoformat')
                        else None
                    )
                }
                for r in ratings
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching ratings for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Fetch completed or cancelled trips for history view
@router.get("/history/{user_id}")
def get_trip_history(
    user_id: str, 
    status: Optional[str] = None, # Filter by COMPLETED/CANCELLED
    limit: int = 10, 
    offset: int = 0, 
    db: Session = Depends(get_db)
):
    """Get trip history for a user"""
    logger.info(f"Fetching trip history for user {user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    query = db.query(Trip).filter(
        (Trip.user_id == user_id) | (Trip.driver_id == user_id)
    )
    
    if status:
        query = query.filter(Trip.status == status)
    else:
        query = query.filter(Trip.status.in_(["COMPLETED", "CANCELLED"]))
    
    trips = query.order_by(
        Trip.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    trip_data = []
    for trip in trips:
        # Get driver/user info
        if trip.user_id == user_id:
            # User is passenger
            other_user = db.query(User).filter(User.id == trip.driver_id).first()
            role = "PASSENGER"
        else:
            # User is driver
            other_user = db.query(User).filter(User.id == trip.user_id).first()
            role = "DRIVER"
        
        # Check if trip has been rated
        is_rated = db.query(Rating).filter(
            Rating.trip_id == trip.id,
            Rating.rater_id == user_id
        ).first() is not None
        
        trip_data.append({
            "trip_id": trip.id,
            "status": trip.status,
            "role": role,
            "other_user_name": other_user.name if other_user else "Unknown",
            "pickup": {"lat": trip.pickup_lat, "lng": trip.pickup_lng},
            "dropoff": {"lat": trip.drop_lat, "lng": trip.drop_lng},
            "fare": trip.fare,
            "completed_at": trip.completed_at.isoformat() if trip.completed_at else None,
            "is_rated": is_rated
        })
    
    return {
        "user_id": user_id,
        "total_count": query.count(),
        "trips": trip_data
    }


# Calculate business KPIs for a user (Total spent or Total earned)
@router.get("/analytics/{user_id}")
def get_user_analytics(user_id: str, db: Session = Depends(get_db)):
    """Get trip analytics for a user"""
    logger.info(f"Fetching analytics for user {user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all completed trips
    completed_trips = db.query(Trip).filter(
        (Trip.user_id == user_id) | (Trip.driver_id == user_id),
        Trip.status == "COMPLETED"
    ).all()
    
    # Calculate analytics
    total_trips = len(completed_trips)
    total_earnings = sum(trip.fare for trip in completed_trips) if user.role == "DRIVER" else 0
    total_spent = sum(trip.fare for trip in completed_trips) if user.role == "USER" else 0
    
    return {
        "user_id": user_id,
        "role": user.role,
        "total_trips": total_trips,
        "average_rating": user.rating,
        "total_ratings": user.total_ratings,
        "total_earnings": round(total_earnings, 2) if user.role == "DRIVER" else None,
        "total_spent": round(total_spent, 2) if user.role == "USER" else None,
    }


# Manual trigger for OTP generation (usually called automatically by accept-ride)
@router.post("/generate-otp")
async def generate_trip_otp(data: TripAction, db: Session = Depends(get_db)):

    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.status != "DRIVER_ASSIGNED":
        raise HTTPException(status_code=400, detail="OTP can only be generated for accepted rides")
    
    otp = generate_otp(data.trip_id)
    trip.otp = otp
    db.commit()
    
    logger.info(f"OTP generated for trip {data.trip_id}: {otp}")
    
    await manager.send_to_many(
        [trip.user_id, trip.driver_id],
        {
            "type": "OTP_GENERATED",
            "trip_id": trip.id,
            "message": "OTP has been generated for this trip"
        }
    )
    
    return {
        "message": "OTP generated successfully",
        "otp": otp,  # In production, send via SMS
        "trip_id": trip.id
    }


# Security check: verify passenger's OTP to transition trip status from ASSIGNED to ONGOING
@router.post("/verify-otp")
async def verify_trip_otp(data: OTPVerification, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.status != "DRIVER_ASSIGNED":
        raise HTTPException(status_code=400, detail="Trip is not ready for OTP verification")
    
    if trip.driver_id != data.user_id:
        raise HTTPException(status_code=403, detail="Only the assigned driver can verify OTP")
    
    result = verify_otp(data.trip_id, data.otp)
    
    if not result['valid']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    trip.otp_verified = True
    # Automatically transition to ONGOING upon successful verification
    trip.status = "ONGOING"
    trip.started_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"Trip {data.trip_id} started with OTP verification")
    
    await manager.send_to_many(
        [trip.user_id, trip.driver_id],
        {
            "type": "TRIP_STARTED",
            "trip_id": trip.id,
            "message": "Trip has started"
        }
    )
    
    return {
        "message": "OTP verified successfully. Trip started!",
        "trip_id": trip.id
    }


# Signal to passenger that driver is moving towards pickup
@router.post("/driver-on-way")
async def driver_on_way(data: DriverLocationUpdate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.driver_id != data.driver_id:
        raise HTTPException(status_code=403, detail="Only the assigned driver can send this update")
    
    if trip.status != "DRIVER_ASSIGNED":
        raise HTTPException(status_code=400, detail="Trip must be assigned before driver can be on the way")
    
    trip.driver_on_way = True
    db.commit()
    
    logger.info(f"Driver {data.driver_id} is on the way for trip {data.trip_id}")
    
    driver = db.query(User).filter(User.id == trip.driver_id).first()
    await manager.send(
        trip.user_id,
        {
            "type": "DRIVER_ON_THE_WAY",
            "trip_id": trip.id,
            "driver_id": trip.driver_id,
            "driver_name": driver.name if driver else "Driver",
            "message": f"🚗 {driver.name if driver else 'Your driver'} is on the way!"
        }
    )
    
    return {
        "message": "Driver status updated. User has been notified.",
        "trip_id": trip.id
    }


# Signal to passenger that driver is waiting outside
@router.post("/driver-arrived")
async def driver_arrived(data: DriverLocationUpdate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.driver_id != data.driver_id:
        raise HTTPException(status_code=403, detail="Only the assigned driver can send this update")
    
    if trip.status != "DRIVER_ASSIGNED":
        raise HTTPException(status_code=400, detail="Trip must be assigned before driver can arrive")
    
    trip.driver_arrived = True
    db.commit()
    
    logger.info(f"Driver {data.driver_id} arrived at pickup for trip {data.trip_id}")
    
    driver = db.query(User).filter(User.id == trip.driver_id).first()
    await manager.send(
        trip.user_id,
        {
            "type": "DRIVER_ARRIVED",
            "trip_id": trip.id,
            "driver_id": trip.driver_id,
            "driver_name": driver.name if driver else "Driver",
            "message": f"✅ {driver.name if driver else 'Your driver'} has arrived!"
        }
    )
    
    return {
        "message": "Driver has arrived. User has been notified.",
        "trip_id": trip.id
    }


# User/Driver rating submission with automatic updating of user's average score
@router.post("/submit-rating")
def submit_rating(data: SubmitRating, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == data.trip_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Rating can only be submitted for completed trips")
    
    # Verify rater is authorized
    ratee_id = None
    if data.rater_id == trip.user_id: # Passenger is rating
        if data.rating_type != "USER_TO_DRIVER": # Expecting passenger to rate driver
            raise HTTPException(status_code=400, detail="Invalid rating_type for passenger rater")
        ratee_id = trip.driver_id
    elif data.rater_id == trip.driver_id: # Driver is rating
        if data.rating_type != "DRIVER_TO_USER": # Expecting driver to rate passenger
            raise HTTPException(status_code=400, detail="Invalid rating_type for driver rater")
        ratee_id = trip.user_id
    else:
        raise HTTPException(status_code=403, detail="Not authorized to rate this trip")

    if ratee_id is None or ratee_id != data.ratee_id: # Ensure determined ratee matches provided ratee
        raise HTTPException(status_code=400, detail="Could not determine valid ratee or provided ratee_id is incorrect")

    # Idempotency check
    existing_rating = db.query(Rating).filter(
        Rating.trip_id == data.trip_id,
        Rating.rater_id == data.rater_id
    ).first()
    
    if existing_rating:
        raise HTTPException(status_code=400, detail="You have already rated this trip")
    
    if data.score < 1 or data.score > 5:
        raise HTTPException(status_code=400, detail="Score must be between 1 and 5")
    
    # Create record
    new_rating = Rating(
        id=generate_id(),
        trip_id=data.trip_id,
        rater_id=data.rater_id,
        ratee_id=ratee_id, # Use the determined ratee_id
        score=data.score,
        comment=data.comment
    )
    
    db.add(new_rating)
    
    # Update target user's cumulative rating and count
    ratee = db.query(User).filter(User.id == data.ratee_id).first()
    if ratee:
        total_score = (ratee.rating or 0) * (ratee.total_ratings or 0)
        total_score += data.score
        
        ratee.total_ratings = (ratee.total_ratings or 0) + 1
        ratee.rating = round(total_score / ratee.total_ratings, 2)
    
    # Update trip rating status
    # Track which party has completed their rating for this specific trip
    if data.rater_id == trip.user_id:
        trip.user_rated = True
    else:
        trip.driver_rated = True
    
    db.commit()
    
    logger.info(f"Rating submitted for trip {data.trip_id} by {data.rater_id}")
    
    return {
        "message": "Rating submitted successfully",
        "trip_id": trip.id,
        "score": data.score,
        "both_rated": trip.user_rated and trip.driver_rated
    }
