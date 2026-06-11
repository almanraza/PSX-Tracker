# routers/stocks.py
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from sqlalchemy.orm import Session
from database.db import get_db
from database import crud
from routers.auth import get_current_user
from models import StockQuote, StockHistory
from services.psx_scraper import get_stock_quote, get_all_quotes, get_stock_history, KNOWN_STOCKS

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get("/", response_model=list[StockQuote])
def list_stocks(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /stocks — all quotes (requires login)"""
    quotes = get_all_quotes()
    crud.log_activity(db, current_user.id, "VIEW_ALL_STOCKS", "Viewed all stocks", ip=request.client.host)

    # Mark which ones are in this user's watchlist
    watchlist_syms = {w.symbol for w in crud.get_watchlist(db, current_user.id)}
    for q in quotes:
        q["in_watchlist"] = q["symbol"] in watchlist_syms
    return quotes


@router.get("/symbols")
def list_symbols():
    """GET /stocks/symbols — list of supported tickers (public)"""
    return list(KNOWN_STOCKS.keys())


@router.get("/{symbol}", response_model=StockQuote)
def get_stock(
    symbol: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /stocks/OGDC — single stock detail (requires login)"""
    symbol = symbol.upper()
    if symbol not in KNOWN_STOCKS:
        raise HTTPException(status_code=404, detail=f"'{symbol}' not found. Check /stocks/symbols.")

    quote = get_stock_quote(symbol)
    quote["in_watchlist"] = crud.is_in_watchlist(db, current_user.id, symbol)

    crud.log_activity(db, current_user.id, "VIEW_STOCK", f"Viewed {symbol}", ip=request.client.host)
    return quote


@router.get("/{symbol}/history", response_model=StockHistory)
def get_history(
    symbol: str,
    request: Request,
    period: str = Query(default="1W", enum=["1D", "1W", "1M", "3M"]),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /stocks/OGDC/history?period=1W — price history chart data"""
    symbol = symbol.upper()
    if symbol not in KNOWN_STOCKS:
        raise HTTPException(status_code=404, detail=f"'{symbol}' not found.")

    crud.log_activity(db, current_user.id, "VIEW_HISTORY", f"{symbol} {period} history", ip=request.client.host)
    return get_stock_history(symbol, period)