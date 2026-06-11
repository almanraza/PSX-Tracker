# database/db.py
# Sets up the SQLAlchemy engine and session factory.
#
# Engine   = the actual connection to the database file
# Session  = a unit of work — open, do stuff, close
# Base     = all your table classes inherit from this
#
# SQLite stores everything in a single file (psx_tracker.db).
# No username, password, or server needed — perfect for development.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./psx_tracker.db")

# connect_args is SQLite-specific — allows multiple threads to share one connection
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal is a factory — call it to get a new session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency — yields a database session for each request,
    then closes it automatically when the request finishes.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist yet. Called once on startup."""
    from database import models   # import here to avoid circular imports
    Base.metadata.create_all(bind=engine)