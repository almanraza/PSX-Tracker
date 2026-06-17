# PSX Stock Tracker

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square&logo=fastapi)
![SQLite](https://img.shields.io/badge/Database-SQLite-orange?style=flat-square&logo=sqlite)
![AWS](https://img.shields.io/badge/Deployed-AWS%20EC2-yellow?style=flat-square&logo=amazon-aws)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

A full-stack **Pakistan Stock Exchange (KSE-100) tracker** with user authentication, a virtual trading portfolio, real-time price alerts, WebSocket live updates, and a dark-mode dashboard — built with FastAPI and deployed on AWS EC2.

🌐 **Live Demo:** [http://13.60.20.203](http://13.60.20.203)

![PSX Tracker Dashboard](screenshot.png)

---

## Features

- **JWT Authentication** — register, login, protected routes
- **Live KSE-100 Data** — real stock prices scraped from public sources, refreshed every 5 minutes
- **Virtual Portfolio Simulator** — PKR 1,000,000 starting balance, buy/sell at live prices, P&L tracking
- **Price Alerts** — set target prices, get in-app notifications when triggered
- **WebSocket Live Updates** — prices pushed to the browser every 15 seconds, no page refresh needed
- **Search & Filter** — search by symbol/company, filter by sector, sort by price/change/volume
- **Activity Log** — every user action tracked (login, views, trades, alerts)
- **Background Scheduler** — auto-refreshes market data and checks alerts every few minutes
- **Rate Limiting** — 120 requests/minute per IP
- **Admin Panel** — platform stats, all users, full activity feed (admin role required)
- **Auto-generated API docs** — Swagger UI at `/docs`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| Auth | JWT (python-jose), bcrypt password hashing |
| Data | Web scraping via cloudscraper + BeautifulSoup |
| Real-time | WebSockets (FastAPI native) |
| Scheduler | APScheduler |
| Rate Limiting | SlowAPI |
| Frontend | Vanilla JS, Chart.js |
| Deployment | AWS EC2 (t3.micro), Nginx reverse proxy, systemd |

---

## Project Structure

```
PSX-Tracker/
│
├── main.py                  # FastAPI app entry point, all routers wired here
├── models.py                # Pydantic request/response schemas
├── requirements.txt
│
├── database/
│   ├── db.py                # SQLAlchemy engine + session + init_db
│   ├── models.py            # DB table definitions (7 tables)
│   └── crud.py              # All DB queries — create, read, update, delete
│
├── routers/
│   ├── auth.py              # POST /auth/register, /auth/login, GET /auth/me
│   ├── stocks.py            # GET /stocks, /stocks/{symbol}, /stocks/search
│   ├── market.py            # GET /market/summary, /market/sectors, /market/movers
│   ├── watchlist.py         # GET/POST/DELETE /watchlist/{symbol}
│   ├── portfolio.py         # GET /portfolio, POST /portfolio/buy, /portfolio/sell
│   ├── alerts.py            # GET/POST/DELETE /alerts, GET /alerts/notifications
│   ├── activity.py          # GET /activity
│   ├── admin.py             # GET /admin/stats, /admin/users, /admin/activity
│   └── ws.py                # WebSocket /ws/prices
│
├── services/
│   ├── psx_scraper.py       # Live PSX data scraping + mock fallback
│   ├── cache.py             # In-memory TTL cache (5 min)
│   └── scheduler.py         # APScheduler — market refresh + alert checker
│
└── static/
    └── index.html           # Full dashboard frontend (auth + app, single file)
```

---

## Database Schema

```
users           → id, email, username, full_name, hashed_password, is_admin
watchlist       → id, user_id, symbol, added_at
activity_log    → id, user_id, action, detail, ip_address, timestamp
portfolios      → id, user_id, cash_balance
holdings        → id, portfolio_id, symbol, quantity, avg_cost
transactions    → id, user_id, symbol, action, quantity, price, total, timestamp
price_alerts    → id, user_id, symbol, target_price, direction, triggered
notifications   → id, user_id, message, read, created_at
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Get JWT token |
| GET | `/auth/me` | Yes | Current user info |
| GET | `/stocks` | Yes | All stock quotes |
| GET | `/stocks/search` | Yes | Search + filter + sort |
| GET | `/stocks/{symbol}` | Yes | Single stock detail |
| GET | `/stocks/{symbol}/history` | Yes | Price chart data |
| GET | `/market/summary` | Yes | KSE-100 index stats |
| GET | `/market/sectors` | Yes | Sector breakdown |
| GET | `/market/movers` | Yes | Top gainers/losers |
| GET | `/watchlist` | Yes | User's watchlist |
| POST | `/watchlist/{symbol}` | Yes | Add to watchlist |
| DELETE | `/watchlist/{symbol}` | Yes | Remove from watchlist |
| GET | `/portfolio` | Yes | Portfolio summary + holdings |
| POST | `/portfolio/buy` | Yes | Buy shares |
| POST | `/portfolio/sell` | Yes | Sell shares |
| GET | `/portfolio/transactions` | Yes | Trade history |
| GET | `/alerts` | Yes | Active price alerts |
| POST | `/alerts` | Yes | Create price alert |
| DELETE | `/alerts/{id}` | Yes | Delete alert |
| GET | `/alerts/notifications` | Yes | In-app notifications |
| GET | `/activity` | Yes | User activity log |
| GET | `/admin/stats` | Admin | Platform stats |
| WS | `/ws/prices` | No | Live price stream |
| GET | `/docs` | No | Swagger UI |

---

## Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/almanraza/PSX-Tracker.git
cd PSX-Tracker

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./psx_tracker.db

# 5. Run the server
uvicorn main:app --reload
```

Open `http://localhost:8000` for the dashboard.
Open `http://localhost:8000/docs` for interactive API docs.

---

## Deployment (AWS EC2)

Deployed on **AWS EC2 t3.micro** (Ubuntu 22.04) with Nginx as reverse proxy and systemd for auto-restart.

```bash
sudo systemctl status psx-tracker    # check status
sudo systemctl restart psx-tracker   # restart after changes
sudo journalctl -u psx-tracker -f    # view live logs
```

---

## Author

**Alman Raza**
- GitHub: [@almanraza](https://github.com/almanraza)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
