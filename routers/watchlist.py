# routers/watchlist.py
# Users can add/remove stocks from their personal watchlist.
# All operations are per-user — protected by JWT.

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.db import get_db
from database import crud
from routers.auth import get_current_user
from services.psx_scraper import get_stock_quote, KNOWN_STOCKS

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("/")
def get_watchlist(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    GET /watchlist
    Returns user's watchlist with live prices attached.
    """
    items = crud.get_watchlist(db, current_user.id)
    result = []
    for item in items:
        quote = get_stock_quote(item.symbol)
        result.append({
            "symbol":   item.symbol,
            "added_at": item.added_at.isoformat(),
            **quote,
        })
    return result


@router.post("/{symbol}")
def add_stock(
    symbol: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """POST /watchlist/OGDC — add stock to watchlist"""
    symbol = symbol.upper()
    if symbol not in KNOWN_STOCKS:
        raise HTTPException(status_code=404, detail=f"'{symbol}' is not a tracked stock.")

    item = crud.add_to_watchlist(db, current_user.id, symbol)
    if item is None:
        raise HTTPException(status_code=400, detail=f"{symbol} is already in your watchlist.")

    crud.log_activity(db, current_user.id, "ADD_WATCHLIST", f"Added {symbol} to watchlist", ip=request.client.host)
    return {"message": f"{symbol} added to watchlist.", "symbol": symbol}


@router.delete("/{symbol}")
def remove_stock(
    symbol: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """DELETE /watchlist/OGDC — remove stock from watchlist"""
    symbol  = symbol.upper()
    removed = crud.remove_from_watchlist(db, current_user.id, symbol)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{symbol} is not in your watchlist.")

    crud.log_activity(db, current_user.id, "REMOVE_WATCHLIST", f"Removed {symbol} from watchlist", ip=request.client.host)
    return {"message": f"{symbol} removed from watchlist."}
