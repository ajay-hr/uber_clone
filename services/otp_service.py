import random
import string
from datetime import datetime, timedelta

# In-memory OTP storage (in production, use Redis or database)
otp_storage = {}

def generate_otp(trip_id: str, length: int = 6) -> str:
    """
    Generate a random OTP for a trip
    """
    otp = ''.join(random.choices(string.digits, k=length))
    
    # Store OTP with expiry time (5 minutes)
    otp_storage[trip_id] = {
        'otp': otp,
        'created_at': datetime.utcnow(),
        'expires_at': datetime.utcnow() + timedelta(minutes=5),
        'attempts': 0,
        'max_attempts': 3
    }
    
    return otp

def verify_otp(trip_id: str, provided_otp: str) -> dict:
    """
    Verify the provided OTP against the stored OTP
    """
    if trip_id not in otp_storage:
        return {
            'valid': False,
            'message': 'OTP expired or not found'
        }
    
    otp_data = otp_storage[trip_id]
    
    # Check if OTP has expired
    if datetime.utcnow() > otp_data['expires_at']:
        del otp_storage[trip_id]
        return {
            'valid': False,
            'message': 'OTP expired'
        }
    
    # Check attempts
    if otp_data['attempts'] >= otp_data['max_attempts']:
        del otp_storage[trip_id]
        return {
            'valid': False,
            'message': 'Maximum OTP verification attempts exceeded'
        }
    
    otp_data['attempts'] += 1
    
    # Verify OTP
    if provided_otp == otp_data['otp']:
        del otp_storage[trip_id]
        return {
            'valid': True,
            'message': 'OTP verified successfully'
        }
    else:
        return {
            'valid': False,
            'message': f'Invalid OTP. {otp_data["max_attempts"] - otp_data["attempts"]} attempts remaining'
        }

def get_otp_for_trip(trip_id: str) -> dict:
    """
    Get OTP details for a trip (for testing purposes)
    """
    if trip_id in otp_storage:
        return otp_storage[trip_id]
    return None

def clear_otp(trip_id: str):
    """
    Clear OTP for a trip
    """
    if trip_id in otp_storage:
        del otp_storage[trip_id]
