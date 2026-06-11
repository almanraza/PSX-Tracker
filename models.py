# models.py
# Pydantic models = the shapes of data coming IN and going OUT of the API.
# These are different from database/models.py (which defines DB tables).
#
# Rule of thumb:
#   database/models.py  → what's stored in the database
#   models.py           → what's sent over HTTP (JSON)

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Body sent to POST /auth/register"""
    email:     EmailStr    # pydantic validates email format automatically
    username:  str
    full_name: str
    password:  str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric only")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strong(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    """Body sent to POST /auth/login"""
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response from login — contains the JWT"""
    access_token: str
    token_type:   str = "bearer"
    user:         "UserOut"   # include user info on login


class UserOut(BaseModel):
    """Safe user info — never include hashed_password here"""
    id:         int
    email:      str
    username:   str
    full_name:  str
    created_at: datetime

    model_config = {"from_attributes": True}  # allows building from SQLAlchemy object


# ── Stock data ────────────────────────────────────────────────────────────────

class StockQuote(BaseModel):
    symbol:        str
    company_name:  str
    sector:        str
    price:         float
    open:          float
    high:          float
    low:           float
    prev_close:    float
    change:        float
    change_pct:    float
    volume:        int
    last_updated:  str
    in_watchlist:  bool = False   # filled in per-user when authenticated


class PricePoint(BaseModel):
    date:  str
    price: float


class StockHistory(BaseModel):
    symbol: str
    period: str
    data:   list[PricePoint]


# ── Market ────────────────────────────────────────────────────────────────────

class MarketSummary(BaseModel):
    index_value:      float
    index_change:     float
    index_change_pct: float
    total_volume:     int
    advancers:        int
    decliners:        int
    unchanged:        int
    last_updated:     str


class SectorWeight(BaseModel):
    sector:     str
    weight_pct: float
    change_pct: float


# ── Watchlist ─────────────────────────────────────────────────────────────────

class WatchlistItem(BaseModel):
    symbol:   str
    added_at: datetime
    model_config = {"from_attributes": True}


# ── Activity ──────────────────────────────────────────────────────────────────

class ActivityItem(BaseModel):
    action:    str
    detail:    Optional[str]
    timestamp: datetime
    model_config = {"from_attributes": True}