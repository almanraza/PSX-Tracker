# routers/auth.py
# Handles user registration, login, and getting current user info.
#
# JWT (JSON Web Token) flow:
#   1. User registers → account stored in DB
#   2. User logs in with email+password → server returns a JWT token
#   3. For every protected request, user sends the token in the header:
#      Authorization: Bearer <token>
#   4. Server decodes the token, finds the user, processes the request

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

from database.db import get_db
from database import crud
from models import RegisterRequest, LoginRequest, TokenResponse, UserOut

load_dotenv()

SECRET_KEY           = os.getenv("SECRET_KEY", "fallback_secret")
ALGORITHM            = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

router        = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login-form")


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: int, username: str) -> str:
    expire  = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    FastAPI dependency injected into protected routes.
    Reads the Bearer token from the Authorization header,
    decodes it, and returns the User from the database.
    """
    payload = decode_token(token)
    user_id = int(payload.get("sub", 0))
    user    = crud.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")
    return user


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """POST /auth/register — create a new account"""
    if crud.get_user_by_email(db, body.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    if crud.get_user_by_username(db, body.username):
        raise HTTPException(status_code=400, detail="Username already taken.")
    user = crud.create_user(db, body.email, body.username, body.full_name, body.password)
    crud.log_activity(db, user.id, "REGISTER", "New account created", ip=request.client.host)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """POST /auth/login — returns JWT token on success"""
    user = crud.authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token = create_access_token(user.id, user.username)
    crud.log_activity(db, user.id, "LOGIN", "User logged in", ip=request.client.host)
    return TokenResponse(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    """GET /auth/me — returns current user profile (requires token)"""
    return current_user