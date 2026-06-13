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
    is_admin   = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships — SQLAlchemy will auto-join these for us
    watchlist     = relationship("Watchlist",     back_populates="user", cascade="all, delete")
    activities    = relationship("ActivityLog",   back_populates="user", cascade="all, delete")
    portfolio     = relationship("Portfolio",     back_populates="user", uselist=False, cascade="all, delete")
    transactions  = relationship("Transaction",   back_populates="user", cascade="all, delete")
    alerts        = relationship("PriceAlert",    back_populates="user", cascade="all, delete")
    notifications = relationship("Notification",back_populates="user", cascade="all, delete")


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


class Portfolio(Base):
    """
    One row per user — tracks virtual cash balance.
    Starting balance: PKR 1,000,000 (set when account is created).
    """
    __tablename__ = "portfolios"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    cash_balance = Column(Float, default=1_000_000.0)
    created_at   = Column(DateTime, default=datetime.utcnow)

    user     = relationship("User", back_populates="portfolio")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete")


class Holding(Base):
    """
    One row per (user, symbol) — shares currently owned.
    avg_cost = average price paid per share (used for P&L calculation).
    Row is deleted when quantity reaches 0.
    """
    __tablename__ = "holdings"

    id           = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol       = Column(String, nullable=False)
    quantity     = Column(Integer, default=0)
    avg_cost     = Column(Float, default=0.0)

    portfolio = relationship("Portfolio", back_populates="holdings")


class Transaction(Base):
    """
    Every buy/sell order — permanent record, never deleted.
    Powers the "transaction history" view.
    """
    __tablename__ = "transactions"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol    = Column(String, nullable=False)
    action    = Column(String, nullable=False)   # "BUY" or "SELL"
    quantity  = Column(Integer, nullable=False)
    price     = Column(Float, nullable=False)    # price per share at execution
    total     = Column(Float, nullable=False)    # quantity * price
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


class PriceAlert(Base):
    """
    User-defined price alerts, checked by the background scheduler.
    direction: "ABOVE" or "BELOW"
    triggered: set True once fired, so it doesn't repeat-notify.
    """
    __tablename__ = "price_alerts"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol        = Column(String, nullable=False)
    target_price  = Column(Float, nullable=False)
    direction     = Column(String, nullable=False)  # "ABOVE" | "BELOW"
    triggered     = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")


class Notification(Base):
    """
    In-app notifications — created when a price alert fires.
    read: whether the user has seen/dismissed it.
    """
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    message    = Column(String, nullable=False)
    read       = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
