# main.py
# App entry point. Everything is wired together here.
# Run with: uvicorn main:app --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database.db import init_db
from routers import auth, stocks, market, watchlist, activity

app = FastAPI(
    title="PSX Stock Tracker API",
    description="Pakistan Stock Exchange tracker with auth, watchlists, and activity logging.",
    version="2.0.0",
)

# CORS — allows the browser dashboard to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire in all routers
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(market.router)
app.include_router(watchlist.router)
app.include_router(activity.router)

# Serve the frontend at /
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def serve_dashboard():
    return FileResponse("static/index.html")

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": "2.0.0"}

# Create DB tables on startup
@app.on_event("startup")
def startup():
    init_db()
    print("✓ Database ready")
    print("✓ PSX Tracker API running at http://localhost:8000")
    print("✓ API docs at http://localhost:8000/docs")
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)