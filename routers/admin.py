# routers/admin.py
# Admin-only endpoints — requires User.is_admin == True.
#
# To make a user an admin, run this once in a Python shell:
#   from database.db import SessionLocal
#   from database.models import User
#   db = SessionLocal()
#   u = db.query(User).filter(User.username == "yourusername").first()
#   u.is_admin = True
#   db.commit()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from database import crud
from routers.auth import get_current_user
from models import PlatformStats, AdminUserItem, ActivityItem

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user=Depends(get_current_user)):
    """Dependency that raises 403 if the current user isn't an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


@router.get("/stats", response_model=PlatformStats)
def platform_stats(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """GET /admin/stats — platform-wide counts"""
    return crud.get_platform_stats(db)


@router.get("/users", response_model=list[AdminUserItem])
def all_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """GET /admin/users — list every registered user"""
    return crud.get_all_users(db)


@router.get("/activity", response_model=list[ActivityItem])
def all_activity(limit: int = 200, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """GET /admin/activity — activity feed across ALL users"""
    return crud.get_all_activity(db, limit=limit)
