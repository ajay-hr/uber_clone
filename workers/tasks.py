from app.services.matching_service import find_nearby_drivers
from app.websocket.manager import manager
from app.database import SessionLocal
from app.models.trip import Trip
from app.workers.celery_worker import celery

@celery.task
def match_driver_task(lat, lng, vehicle_type, trip_id):
    db = SessionLocal()

    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not trip or trip.status != "REQUESTED":
        return

    driver_ids = find_nearby_drivers(lat, lng, vehicle_type)

    if not driver_ids:
        print("No drivers found")
        return

    import asyncio

    for driver_id in driver_ids:
        try:
            asyncio.run(
                manager.send(
                    driver_id,
                    {
                        "type": "NEW_RIDE_REQUEST",
                        "trip_id": trip.id,
                        "pickup": {
                            "lat": trip.pickup_lat,
                            "lng": trip.pickup_lng
                        },
                        "vehicle_type": vehicle_type
                    }
                )
            )
        except Exception as e:
            print(f"Error sending to {driver_id}: {e}")