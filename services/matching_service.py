import redis
from app.config import REDIS_HOST, REDIS_PORT
from app.models.driver_profile import DriverProfile
from app.database import SessionLocal

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def update_driver_location(driver_id, lat, lng):
    r.geoadd("drivers", (lng, lat, driver_id))


def find_nearby_drivers(lat, lng, vehicle_type, radius=5):
    driver_ids = r.georadius("drivers", lng, lat, radius, unit="km")

    db = SessionLocal()

    drivers = db.query(DriverProfile).filter(
        DriverProfile.driver_id.in_(driver_ids),
        DriverProfile.vehicle_type == vehicle_type
    ).all()

    return [d.driver_id for d in drivers]


# LOCKING
def acquire_lock(key, timeout=5):
    return r.set(key, "locked", nx=True, ex=timeout)


def release_lock(key):
    r.delete(key)