from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, ride
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Enable CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For testing purposes, allows everything
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

app.include_router(auth.router, prefix="/auth")
app.include_router(ride.router, prefix="/ride")
