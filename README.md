# PSX Stock Tracker

Real-time Pakistan Stock Exchange dashboard with user authentication, personal watchlists, and activity tracking.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![SQLite](https://img.shields.io/badge/Database-SQLite-orange)

---

## Features

- JWT login / register system
- Live KSE-100 stock quotes (Yahoo Finance, ~15 min delay)
- Price history charts (1D / 1W / 1M / 3M)
- Personal watchlist per user (stored in database)
- Full activity log — every action tracked
- Auto-generated API docs at `/docs`
- Deployable to Railway in 2 minutes

---

## Run locally

```bash
# 1. Clone and enter folder
git clone https://github.com/yourusername/psx-stock-tracker
cd psx-stock-tracker

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn main:app --reload
```

Open http://localhost:8000 — dashboard loads with login screen.  
Open http://localhost:8000/docs — full interactive API docs.

---

## Deploy to Railway (free)

1. Push this project to a GitHub repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo — Railway auto-detects Python and uses `Procfile`
4. Add environment variables in Railway dashboard:
   ```
   SECRET_KEY=your_random_secret_here
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   DATABASE_URL=sqlite:///./psx_tracker.db
   ```
5. Done — Railway gives you a public URL like `https://psx-tracker.up.railway.app`

> **Update the API URL**: Once deployed, open `static/index.html` and change  
> `const API = 'http://localhost:8000'`  
> to your Railway URL, then redeploy.

---

## Project structure

```
psx-tracker/
├── main.py                  # FastAPI app entry point
├── models.py                # Pydantic request/response schemas
├── Procfile                 # Railway/Heroku start command
├── railway.json             # Railway config
├── requirements.txt
│
├── database/
│   ├── db.py                # SQLAlchemy engine + session
│   ├── models.py            # DB table definitions (users, watchlist, activity)
│   └── crud.py              # All DB queries (create, read, update, delete)
│
├── routers/
│   ├── auth.py              # POST /auth/register, /auth/login, GET /auth/me
│   ├── stocks.py            # GET /stocks, /stocks/{symbol}, /stocks/{symbol}/history
│   ├── market.py            # GET /market/summary, /market/sectors, /market/movers
│   ├── watchlist.py         # GET/POST/DELETE /watchlist/{symbol}
│   └── activity.py          # GET /activity
│
├── services/
│   ├── psx_scraper.py       # Yahoo Finance data + mock fallback
│   └── cache.py             # 5-minute TTL in-memory cache
│
└── static/
    └── index.html           # Full dashboard frontend (login + app)
```

---

## API endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Get JWT token |
| GET | `/auth/me` | Yes | Current user info |
| GET | `/stocks` | Yes | All stock quotes |
| GET | `/stocks/{symbol}` | Yes | Single stock detail |
| GET | `/stocks/{symbol}/history?period=1W` | Yes | Price chart data |
| GET | `/market/summary` | Yes | KSE-100 index stats |
| GET | `/market/sectors` | Yes | Sector breakdown |
| GET | `/market/movers` | Yes | Top gainers/losers |
| GET | `/watchlist` | Yes | User's watchlist with prices |
| POST | `/watchlist/{symbol}` | Yes | Add to watchlist |
| DELETE | `/watchlist/{symbol}` | Yes | Remove from watchlist |
| GET | `/activity` | Yes | User's activity history |

---

## Data source

Yahoo Finance via `yfinance` — PSX stocks listed under `.KA` suffix (e.g. `OGDC.KA`).  
Data is real and delayed ~15 minutes. Falls back to seeded mock data when Yahoo is unreachable.

## Tech stack

**Backend:** Python, FastAPI, SQLAlchemy, SQLite, JWT, bcrypt  
**Data:** yfinance (Yahoo Finance)  
**Frontend:** Vanilla JS, Chart.js  
**Deployment:** Railway
