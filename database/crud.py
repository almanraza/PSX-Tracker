# database/crud.py
# All database operations in one place.
# CRUD = Create, Read, Update, Delete
#
# Routers call these functions — they never write SQL directly.
# This separation means if you ever swap SQLite for PostgreSQL,
# you only change this file.

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from database.models import User, Watchlist, ActivityLog
from passlib.context import CryptContext

# bcrypt hasher — this is what makes passwords safe to store
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Turn 'mypassword123' into '$2b$12$...' (bcrypt hash)"""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Returns True if plain matches the stored hash."""
    return pwd_context.verify(plain, hashed)


# ── User CRUD ────────────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, email: str, username: str, full_name: str, password: str) -> User:
    """Create a new user. Password is hashed before storing."""
    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)   # reload from DB to get the auto-assigned id
    return user

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return user if email+password match, else None."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ── Watchlist CRUD ───────────────────────────────────────────────────────────

def get_watchlist(db: Session, user_id: int) -> list[Watchlist]:
    return (db.query(Watchlist)
              .filter(Watchlist.user_id == user_id)
              .order_by(desc(Watchlist.added_at))
              .all())

def add_to_watchlist(db: Session, user_id: int, symbol: str) -> Watchlist | None:
    """Add symbol to watchlist. Returns None if already exists."""
    exists = (db.query(Watchlist)
                .filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol)
                .first())
    if exists:
        return None   # already in watchlist
    item = Watchlist(user_id=user_id, symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def remove_from_watchlist(db: Session, user_id: int, symbol: str) -> bool:
    """Remove symbol. Returns True if it existed, False if not found."""
    item = (db.query(Watchlist)
              .filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol)
              .first())
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True

def is_in_watchlist(db: Session, user_id: int, symbol: str) -> bool:
    return (db.query(Watchlist)
              .filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol)
              .first()) is not None


# ── Activity Log CRUD ────────────────────────────────────────────────────────

def log_activity(db: Session, user_id: int, action: str, detail: str = None, ip: str = None):
    """
    Record a user action. Called throughout the app automatically.
    action examples: "LOGIN", "VIEW_STOCK", "ADD_WATCHLIST", "VIEW_MARKET"
    """
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        detail=detail,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()

def get_activity(db: Session, user_id: int, limit: int = 50) -> list[ActivityLog]:
    """Get the N most recent activities for a user."""
    return (db.query(ActivityLog)
              .filter(ActivityLog.user_id == user_id)
              .order_by(desc(ActivityLog.timestamp))
              .limit(limit)
              .all())