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
from database.models import (
    User, Watchlist, ActivityLog,
    Portfolio, Holding, Transaction, PriceAlert, Notification
)
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
    """Create a new user. Password is hashed before storing.
    Also creates a Portfolio with PKR 1,000,000 starting cash."""
    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)   # reload from DB to get the auto-assigned id

    # Every new user gets a virtual trading portfolio
    portfolio = Portfolio(user_id=user.id, cash_balance=1_000_000.0)
    db.add(portfolio)
    db.commit()

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


# ── Portfolio CRUD ───────────────────────────────────────────────────────────

def get_portfolio(db: Session, user_id: int) -> Portfolio:
    """Get user's portfolio. Creates one if missing (safety net for old accounts)."""
    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not portfolio:
        portfolio = Portfolio(user_id=user_id, cash_balance=1_000_000.0)
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    return portfolio


def get_holding(db: Session, portfolio_id: int, symbol: str) -> Holding | None:
    return (db.query(Holding)
              .filter(Holding.portfolio_id == portfolio_id, Holding.symbol == symbol)
              .first())


def get_all_holdings(db: Session, portfolio_id: int) -> list[Holding]:
    return (db.query(Holding)
              .filter(Holding.portfolio_id == portfolio_id, Holding.quantity > 0)
              .all())


def buy_stock(db: Session, user_id: int, symbol: str, quantity: int, price: float) -> dict:
    """
    Execute a BUY order.
    - Checks the user has enough cash
    - Updates (or creates) the Holding with new average cost
    - Deducts cash from Portfolio
    - Records a Transaction
    Returns {"success": bool, "message": str}
    """
    portfolio = get_portfolio(db, user_id)
    cost = round(quantity * price, 2)

    if cost > portfolio.cash_balance:
        return {"success": False, "message": "Insufficient funds for this purchase."}

    holding = get_holding(db, portfolio.id, symbol)
    if holding:
        # Recalculate weighted average cost
        total_cost = (holding.avg_cost * holding.quantity) + cost
        holding.quantity += quantity
        holding.avg_cost = round(total_cost / holding.quantity, 2)
    else:
        holding = Holding(portfolio_id=portfolio.id, symbol=symbol, quantity=quantity, avg_cost=price)
        db.add(holding)

    portfolio.cash_balance = round(portfolio.cash_balance - cost, 2)

    tx = Transaction(user_id=user_id, symbol=symbol, action="BUY",
                      quantity=quantity, price=price, total=cost)
    db.add(tx)
    db.commit()
    return {"success": True, "message": f"Bought {quantity} shares of {symbol} at PKR {price}."}


def sell_stock(db: Session, user_id: int, symbol: str, quantity: int, price: float) -> dict:
    """
    Execute a SELL order.
    - Checks the user owns enough shares
    - Reduces (or removes) the Holding
    - Adds proceeds to Portfolio cash
    - Records a Transaction
    """
    portfolio = get_portfolio(db, user_id)
    holding   = get_holding(db, portfolio.id, symbol)

    if not holding or holding.quantity < quantity:
        owned = holding.quantity if holding else 0
        return {"success": False, "message": f"You only own {owned} shares of {symbol}."}

    proceeds = round(quantity * price, 2)
    holding.quantity -= quantity
    if holding.quantity == 0:
        db.delete(holding)   # cosmetic — remove empty holdings

    portfolio.cash_balance = round(portfolio.cash_balance + proceeds, 2)

    tx = Transaction(user_id=user_id, symbol=symbol, action="SELL",
                      quantity=quantity, price=price, total=proceeds)
    db.add(tx)
    db.commit()
    return {"success": True, "message": f"Sold {quantity} shares of {symbol} at PKR {price}."}


def get_transactions(db: Session, user_id: int, limit: int = 100) -> list[Transaction]:
    return (db.query(Transaction)
              .filter(Transaction.user_id == user_id)
              .order_by(desc(Transaction.timestamp))
              .limit(limit)
              .all())


# ── Price Alert CRUD ─────────────────────────────────────────────────────────

def create_alert(db: Session, user_id: int, symbol: str, target_price: float, direction: str) -> PriceAlert:
    alert = PriceAlert(user_id=user_id, symbol=symbol, target_price=target_price, direction=direction)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alerts(db: Session, user_id: int, active_only: bool = True) -> list[PriceAlert]:
    q = db.query(PriceAlert).filter(PriceAlert.user_id == user_id)
    if active_only:
        q = q.filter(PriceAlert.triggered == False)
    return q.order_by(desc(PriceAlert.created_at)).all()


def delete_alert(db: Session, user_id: int, alert_id: int) -> bool:
    alert = (db.query(PriceAlert)
               .filter(PriceAlert.id == alert_id, PriceAlert.user_id == user_id)
               .first())
    if not alert:
        return False
    db.delete(alert)
    db.commit()
    return True


def get_all_active_alerts(db: Session) -> list[PriceAlert]:
    """Used by the background scheduler — fetches alerts across ALL users."""
    return db.query(PriceAlert).filter(PriceAlert.triggered == False).all()


def trigger_alert(db: Session, alert: PriceAlert):
    """Mark an alert as triggered and create a notification for the user."""
    alert.triggered = True
    direction_word = "risen above" if alert.direction == "ABOVE" else "fallen below"
    notif = Notification(
        user_id=alert.user_id,
        message=f"{alert.symbol} has {direction_word} PKR {alert.target_price:.2f}",
    )
    db.add(notif)
    db.commit()


# ── Notification CRUD ────────────────────────────────────────────────────────

def get_notifications(db: Session, user_id: int, unread_only: bool = False, limit: int = 50) -> list[Notification]:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.read == False)
    return q.order_by(desc(Notification.created_at)).limit(limit).all()


def mark_notification_read(db: Session, user_id: int, notif_id: int) -> bool:
    notif = (db.query(Notification)
               .filter(Notification.id == notif_id, Notification.user_id == user_id)
               .first())
    if not notif:
        return False
    notif.read = True
    db.commit()
    return True


def mark_all_notifications_read(db: Session, user_id: int):
    (db.query(Notification)
       .filter(Notification.user_id == user_id, Notification.read == False)
       .update({"read": True}))
    db.commit()


# ── Admin CRUD ───────────────────────────────────────────────────────────────

def get_all_users(db: Session) -> list[User]:
    return db.query(User).order_by(desc(User.created_at)).all()


def get_all_activity(db: Session, limit: int = 200) -> list[ActivityLog]:
    return (db.query(ActivityLog)
              .order_by(desc(ActivityLog.timestamp))
              .limit(limit)
              .all())


def get_platform_stats(db: Session) -> dict:
    total_users = db.query(User).count()
    total_tx    = db.query(Transaction).count()
    total_acts  = db.query(ActivityLog).count()
    total_alerts = db.query(PriceAlert).count()
    return {
        "total_users": total_users,
        "total_transactions": total_tx,
        "total_activity_events": total_acts,
        "total_alerts": total_alerts,
    }

