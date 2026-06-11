# routers/market.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from database.db import get_db
from database import crud
from routers.auth import get_current_user
from models import MarketSummary, SectorWeight
from services.psx_scraper import get_market_summary, get_sector_weights, get_all_quotes

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/summary", response_model=MarketSummary)
def market_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /market/summary — KSE-100 index, volume, advancers/decliners"""
    crud.log_activity(db, current_user.id, "VIEW_MARKET", "Viewed market summary", ip=request.client.host)
    return get_market_summary()


@router.get("/sectors", response_model=list[SectorWeight])
def sector_breakdown(current_user=Depends(get_current_user)):
    """GET /market/sectors — sector weights"""
    return get_sector_weights()


@router.get("/movers")
def top_movers(
    top_n: int = 5,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /market/movers?top_n=5 — top gainers and losers"""
    quotes = get_all_quotes()
    crud.log_activity(db, current_user.id, "VIEW_MOVERS", "Viewed top movers", ip=request.client.host)
    sorted_q = sorted(quotes, key=lambda q: q["change_pct"], reverse=True)
    return {
        "gainers": sorted_q[:top_n],
        "losers":  sorted_q[-top_n:][::-1],
    }