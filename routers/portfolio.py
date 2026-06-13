# routers/portfolio.py
# Virtual trading simulator.
# Every user starts with PKR 1,000,000 virtual cash (set on registration).
# Buy/sell executes at the current live (or simulated) market price.

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.db import get_db
from database import crud
from routers.auth import get_current_user
from models import OrderRequest, PortfolioSummary, HoldingItem, TransactionItem
from services.psx_scraper import get_stock_quote, KNOWN_STOCKS

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/", response_model=PortfolioSummary)
def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    GET /portfolio
    Returns cash balance, all holdings with live valuations, and total P&L.
    """
    portfolio = crud.get_portfolio(db, current_user.id)
    holdings  = crud.get_all_holdings(db, portfolio.id)

    holding_items = []
    holdings_value = 0.0
    total_cost     = 0.0

    for h in holdings:
        quote = get_stock_quote(h.symbol)
        current_price = quote["price"]
        market_value  = round(current_price * h.quantity, 2)
        cost_basis    = round(h.avg_cost * h.quantity, 2)
        gain_loss     = round(market_value - cost_basis, 2)
        gain_loss_pct = round((gain_loss / cost_basis) * 100, 2) if cost_basis else 0.0

        holding_items.append(HoldingItem(
            symbol=h.symbol,
            company_name=quote["company_name"],
            quantity=h.quantity,
            avg_cost=h.avg_cost,
            current_price=current_price,
            market_value=market_value,
            gain_loss=gain_loss,
            gain_loss_pct=gain_loss_pct,
        ))
        holdings_value += market_value
        total_cost      += cost_basis

    total_value = round(portfolio.cash_balance + holdings_value, 2)
    total_gain  = round(holdings_value - total_cost, 2)
    total_gain_pct = round((total_gain / total_cost) * 100, 2) if total_cost else 0.0

    return PortfolioSummary(
        cash_balance=portfolio.cash_balance,
        holdings_value=round(holdings_value, 2),
        total_value=total_value,
        total_gain_loss=total_gain,
        total_gain_loss_pct=total_gain_pct,
        holdings=holding_items,
    )


@router.post("/buy")
def buy(
    order: OrderRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /portfolio/buy
    Body: {"symbol": "OGDC", "quantity": 10}
    Buys at the current live price. Fails if insufficient cash.
    """
    symbol = order.symbol.upper()
    if symbol not in KNOWN_STOCKS:
        raise HTTPException(status_code=404, detail=f"'{symbol}' is not a tracked stock.")

    quote  = get_stock_quote(symbol)
    result = crud.buy_stock(db, current_user.id, symbol, order.quantity, quote["price"])

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    crud.log_activity(db, current_user.id, "BUY_STOCK",
                       f"Bought {order.quantity} {symbol} @ {quote['price']}",
                       ip=request.client.host)
    return result


@router.post("/sell")
def sell(
    order: OrderRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /portfolio/sell
    Body: {"symbol": "OGDC", "quantity": 10}
    Sells at the current live price. Fails if user doesn't own enough shares.
    """
    symbol = order.symbol.upper()
    if symbol not in KNOWN_STOCKS:
        raise HTTPException(status_code=404, detail=f"'{symbol}' is not a tracked stock.")

    quote  = get_stock_quote(symbol)
    result = crud.sell_stock(db, current_user.id, symbol, order.quantity, quote["price"])

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    crud.log_activity(db, current_user.id, "SELL_STOCK",
                       f"Sold {order.quantity} {symbol} @ {quote['price']}",
                       ip=request.client.host)
    return result


@router.get("/transactions", response_model=list[TransactionItem])
def get_transactions(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /portfolio/transactions — full buy/sell history"""
    return crud.get_transactions(db, current_user.id, limit=limit)
