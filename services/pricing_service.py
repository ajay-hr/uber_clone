from app.services.distance_service import haversine

# Vehicle type pricing multipliers
VEHICLE_MULTIPLIERS = {
    "BIKE": 0.6,
    "AUTO": 0.9,
    "MINI_CAR": 1.3,
    "FAMILY_CAR": 1.8
}

def calculate_surge(demand, supply):
    if supply == 0:
        return 1.5
    # Surge price between 1.0x and 1.5x
    return min(1.5, max(1.0, demand / supply))

def calculate_fare(lat1, lng1, lat2, lng2, vehicle_type="BIKE"):
    base_fare = 15      # ₹15 base fare
    per_km = 7          # ₹7 per km

    distance = haversine(lat1, lng1, lat2, lng2)

    demand = 10
    supply = 5

    surge = calculate_surge(demand, supply)

    # Get vehicle multiplier
    vehicle_multiplier = VEHICLE_MULTIPLIERS.get(vehicle_type, 1.0)

    # Calculate fare in rupees
    fare = (base_fare + distance * per_km) * surge * vehicle_multiplier
    return round(fare, 2)

def get_all_vehicle_prices(lat1, lng1, lat2, lng2):
    """Calculate fare for all vehicle types"""
    prices = {}
    for vehicle_type in VEHICLE_MULTIPLIERS.keys():
        prices[vehicle_type] = calculate_fare(lat1, lng1, lat2, lng2, vehicle_type)
    return prices