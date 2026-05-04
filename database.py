from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL
from fastapi import HTTPException

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    raise HTTPException(
            status_code=400,
            detail="Database URL is invalid."
        )

engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"}  # required for Supabase
)


SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
