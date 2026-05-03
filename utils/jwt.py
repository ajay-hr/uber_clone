from jose import jwt
from app.config import SECRET_KEY

def create_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm="HS256")