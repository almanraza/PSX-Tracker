# main.py
# App entry point. Run with: uvicorn main:app --reload

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database.db import init_db
from services.scheduler import start_scheduler, stop_scheduler
from routers import auth, stocks, market, watchlist, activity, portfolio, alerts, admin, ws


# ── Rate limiter ─────────────────────────────────────────────────────────────
# Limits requests per IP address. Protects the PSX scraper from abuse
# and keeps the free Railway instance from being overwhelmed.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    init_db()
    print("✓ Database tables ready")
    start_scheduler()
    print("✓ PSX Tracker API is live")
    yield
    # --- shutdown ---
    stop_scheduler()


app = FastAPI(
    title="PSX Stock Tracker API",
    description="Pakistan Stock Exchange tracker with auth, portfolio simulator, alerts, and live updates.",
    version="3.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — lets the browser dashboard call the API from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(market.router)
app.include_router(watchlist.router)
app.include_router(activity.router)
app.include_router(portfolio.router)
app.include_router(alerts.router)
app.include_router(admin.router)
app.include_router(ws.router)

# Serve the static dashboard at /
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def serve_dashboard():
    return FileResponse("static/index.html")

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": "3.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
