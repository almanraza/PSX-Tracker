# routers/activity.py
# Returns the user's activity history — every action they've taken.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database.db import get_db
from database import crud
from routers.auth import get_current_user
from models import ActivityItem

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("/", response_model=list[ActivityItem])
def get_my_activity(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    GET /activity?limit=50
    Returns this user's recent actions (login, views, watchlist changes).
    Useful for the activity feed in the dashboard.
    """
    return crud.get_activity(db, current_user.id, limit=limit)
