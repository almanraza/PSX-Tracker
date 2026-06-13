# services/scheduler.py
# Background job scheduler using APScheduler.
#
# Two recurring jobs:
#   1. refresh_market_data  — every 5 min, pre-warms the stock cache so
#      the first user of the day doesn't wait for a slow scrape.
#   2. check_price_alerts   — every 2 min, compares live prices against
#      all active PriceAlerts and fires notifications when triggered.
#
# Runs in-process alongside FastAPI (fine for a single-instance deployment
# like Railway's free tier — no separate worker needed).

from apscheduler.schedulers.background import BackgroundScheduler
from database.db import SessionLocal
from database import crud
from services.psx_scraper import get_all_quotes, get_market_summary, get_sector_weights

scheduler = BackgroundScheduler()


def refresh_market_data():
    """
    Pre-warm the in-memory stock cache.
    Calling these populates services.cache.stock_cache for all symbols,
    so subsequent user requests are served instantly from cache.
    """
    try:
        quotes = get_all_quotes()
        get_market_summary(quotes)
        get_sector_weights()
        print(f"[scheduler] refreshed market data for {len(quotes)} stocks")
    except Exception as e:
        print(f"[scheduler] refresh_market_data error: {e}")


def check_price_alerts():
    """
    Check every active price alert against the current live price.
    If triggered, mark it as fired and create a Notification for the user.
    """
    db = SessionLocal()
    try:
        alerts = crud.get_all_active_alerts(db)
        if not alerts:
            return

        # Build a lookup of current prices (one scrape covers all symbols)
        quotes = get_all_quotes()
        price_map = {q["symbol"]: q["price"] for q in quotes}

        fired = 0
        for alert in alerts:
            price = price_map.get(alert.symbol)
            if price is None:
                continue

            should_fire = (
                (alert.direction == "ABOVE" and price >= alert.target_price) or
                (alert.direction == "BELOW" and price <= alert.target_price)
            )
            if should_fire:
                crud.trigger_alert(db, alert)
                fired += 1

        if fired:
            print(f"[scheduler] fired {fired} price alert(s)")
    except Exception as e:
        print(f"[scheduler] check_price_alerts error: {e}")
    finally:
        db.close()


def start_scheduler():
    """Called once on app startup."""
    scheduler.add_job(refresh_market_data, "interval", minutes=5, id="refresh_market_data", next_run_time=None)
    scheduler.add_job(check_price_alerts,  "interval", minutes=2, id="check_price_alerts")
    scheduler.start()
    # Run once immediately on startup so cache isn't empty
    refresh_market_data()
    print("[scheduler] started — market data every 5min, alerts every 2min")


def stop_scheduler():
    scheduler.shutdown(wait=False)
