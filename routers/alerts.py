# routers/alerts.py
# Users set price alerts ("notify me when OGDC goes above 200").
# A background scheduler (see services/scheduler.py) checks these
# every few minutes and creates a Notification when triggered.

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.db import get_db
from database import crud
from routers.auth import get_current_user
from models import AlertRequest, AlertItem, NotificationItem
from services.psx_scraper import KNOWN_STOCKS

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=list[AlertItem])
def list_alerts(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /alerts?active_only=true — user's price alerts"""
    return crud.get_alerts(db, current_user.id, active_only=active_only)


@router.post("/", response_model=AlertItem, status_code=201)
def create_alert(
    body: AlertRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /alerts
    Body: {"symbol": "OGDC", "target_price": 200, "direction": "ABOVE"}
    direction: "ABOVE" fires when price >= target, "BELOW" fires when price <= target.
    """
    symbol = body.symbol.upper()
    if symbol not in KNOWN_STOCKS:
        raise HTTPException(status_code=404, detail=f"'{symbol}' is not a tracked stock.")

    alert = crud.create_alert(db, current_user.id, symbol, body.target_price, body.direction)
    crud.log_activity(db, current_user.id, "CREATE_ALERT",
                       f"Alert: {symbol} {body.direction} {body.target_price}",
                       ip=request.client.host)
    return alert


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """DELETE /alerts/3 — remove an alert"""
    removed = crud.delete_alert(db, current_user.id, alert_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"message": "Alert deleted."}


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_model=list[NotificationItem])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """GET /alerts/notifications?unread_only=true"""
    return crud.get_notifications(db, current_user.id, unread_only=unread_only)


@router.post("/notifications/{notif_id}/read")
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """POST /alerts/notifications/5/read — mark one notification as read"""
    ok = crud.mark_notification_read(db, current_user.id, notif_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"message": "Marked as read."}


@router.post("/notifications/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """POST /alerts/notifications/read-all — mark all as read"""
    crud.mark_all_notifications_read(db, current_user.id)
    return {"message": "All notifications marked as read."}
