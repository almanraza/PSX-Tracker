# database/models.py
# Defines the actual database tables using SQLAlchemy ORM.
# Each class here becomes one table in psx_tracker.db
#
# ORM = Object Relational Mapper — lets you work with tables as Python
# classes instead of writing raw SQL.

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base


class User(Base):
    """
    The users table.
    Stores account credentials and profile info.
    Password is stored as a bcrypt hash — never plain text.
    """
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    username   = Column(String, unique=True, index=True, nullable=False)
    full_name  = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships — SQLAlchemy will auto-join these for us
    watchlist  = relationship("Watchlist",   back_populates="user", cascade="all, delete")
    activities = relationship("ActivityLog", back_populates="user", cascade="all, delete")


class Watchlist(Base):
    """
    The watchlist table.
    Each row = one stock that one user is watching.
    Multiple users can watch the same stock (each gets their own row).
    """
    __tablename__ = "watchlist"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol     = Column(String, nullable=False)    # e.g. "OGDC"
    added_at   = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="watchlist")


class ActivityLog(Base):
    """
    The activity_log table.
    Every meaningful user action gets recorded here automatically.
    Examples: login, viewed stock, added to watchlist, refreshed market
    """
    __tablename__ = "activity_log"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    action      = Column(String, nullable=False)   # e.g. "VIEW_STOCK"
    detail      = Column(Text, nullable=True)      # e.g. "Viewed OGDC"
    ip_address  = Column(String, nullable=True)
    timestamp   = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activities")