# services/psx_scraper.py
#
# Data source: hamariweb.com — a free, public Pakistani finance portal that
# publishes a full live PSX table (LDCP, Open, High, Low, Current, Change, Volume)
# organized by sector, refreshed every ~5 minutes. No API key, no auth.
#
# URL: https://hamariweb.com/finance/stockexchanges/kse.aspx
#
# Fallback chain:
#   1. hamariweb.com live table (real PSX data)
#   2. Seeded mock data (consistent per day) — used only if the site is unreachable

import re
import httpx
import cloudscraper
from datetime import datetime, timedelta
import random
from services.cache import stock_cache

HAMARIWEB_URL = "https://hamariweb.com/finance/stockexchanges/kse.aspx"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Stock registry ─────────────────────────────────────────────────────────
# "match" = the display name used on hamariweb (used to find the row)
KNOWN_STOCKS: dict[str, dict] = {
    "OGDC":  {"name": "Oil & Gas Development Co.", "sector": "Energy",        "match": "OGDC"},
    "PSO":   {"name": "Pakistan State Oil",         "sector": "Energy",        "match": "PSO"},
    "PPL":   {"name": "Pakistan Petroleum Ltd.",    "sector": "Energy",        "match": "PPL"},
    "LUCK":  {"name": "Lucky Cement",               "sector": "Cement",        "match": "Lucky Cement"},
    "MLCF":  {"name": "Maple Leaf Cement",          "sector": "Cement",        "match": "Maple Leaf"},
    "MCB":   {"name": "MCB Bank",                   "sector": "Banking",       "match": "MCB Bank"},
    "HBL":   {"name": "Habib Bank Ltd.",            "sector": "Banking",       "match": "HBL"},
    "UBL":   {"name": "United Bank Limited",        "sector": "Banking",       "match": "UBL"},
    "ENGRO": {"name": "Engro Corporation",          "sector": "Conglomerate",  "match": "ENGROH"},
    "FFC":   {"name": "Fauji Fertilizer Co.",       "sector": "Fertilizer",    "match": "FFC"},
    "HUBC":  {"name": "Hub Power Company",          "sector": "Power",         "match": "HUBC"},
    "TRG":   {"name": "TRG Pakistan",               "sector": "Technology",   "match": "TRG"},
}

SECTOR_DATA = [
    {"sector": "Energy",       "weight_pct": 28.0},
    {"sector": "Banking",      "weight_pct": 22.0},
    {"sector": "Cement",       "weight_pct": 15.0},
    {"sector": "Technology",   "weight_pct": 12.0},
    {"sector": "Fertilizer",   "weight_pct": 10.0},
    {"sector": "Power",        "weight_pct":  7.0},
    {"sector": "Conglomerate", "weight_pct":  4.0},
    {"sector": "Other",        "weight_pct":  2.0},
]

# Realistic fallback prices (PKR)
BASE_PRICES = {
    "OGDC": 320.0, "PSO": 350.0, "PPL": 225.0, "LUCK": 475.0,
    "MLCF": 106.0, "MCB": 245.0, "HBL": 315.0, "UBL": 400.0,
    "ENGRO": 260.0,"FFC": 555.0, "HUBC": 213.0, "TRG":  70.0,
}

KSE100_BASE = 156000.0


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ── Scraper ──────────────────────────────────────────────────────────────────
import time
_table_cache: dict = {}
_table_cache_ts: float = 0.0
TABLE_TTL = 300  # 5 minutes — matches hamariweb's own refresh rate


def _fetch_table_html() -> str | None:
    """Fetch the raw HTML of the KSE live table page."""
    try:
        scraper = cloudscraper.create_scraper()
        r = scraper.get(HAMARIWEB_URL, headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.text) > 5000:
            return r.text
    except Exception as e:
        print(f"[hamariweb] cloudscraper failed: {e}")

    # Fallback to plain httpx
    try:
        r = httpx.get(HAMARIWEB_URL, headers=HEADERS, timeout=20, follow_redirects=True)
        if r.status_code == 200 and len(r.text) > 5000:
            return r.text
    except Exception as e:
        print(f"[hamariweb] httpx failed: {e}")

    return None


def _parse_table(html: str) -> dict[str, dict]:
    """
    Parse the hamariweb KSE table into { display_name: {ldcp, open, high, low, current, change, volume} }
    Table rows look like:
      <tr><td>Name</td><td>LDCP</td><td>Open</td><td>High</td><td>Low</td><td>Current</td><td>Change</td><td>Volume</td></tr>
    We use regex on <tr>...</tr> blocks to avoid needing a full HTML parser.
    """
    results = {}
    # Match each table row's cell contents
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
    cell_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
    tag_strip = re.compile(r"<[^>]+>")

    for row_match in row_pattern.finditer(html):
        row_html = row_match.group(1)
        cells = cell_pattern.findall(row_html)
        if len(cells) != 8:
            continue
        # Clean each cell: strip tags, whitespace, commas
        clean = [tag_strip.sub("", c).strip().replace(",", "") for c in cells]
        name = clean[0]
        if not name or name.upper() in ("SCRIP",):
            continue
        try:
            ldcp, open_, high, low, current, change, volume = (
                float(clean[1]), float(clean[2]), float(clean[3]),
                float(clean[4]), float(clean[5]), float(clean[6]), int(float(clean[7]))
            )
        except (ValueError, IndexError):
            continue

        results[name] = {
            "ldcp": ldcp, "open": open_, "high": high, "low": low,
            "current": current, "change": change, "volume": volume,
        }

    return results


def _get_live_table() -> dict[str, dict]:
    """Cache the parsed table for TABLE_TTL seconds."""
    global _table_cache, _table_cache_ts
    if _table_cache and (time.time() - _table_cache_ts) < TABLE_TTL:
        return _table_cache

    html = _fetch_table_html()
    if not html:
        return _table_cache  # return stale cache if fetch failed, else {}

    parsed = _parse_table(html)
    if parsed:
        _table_cache = parsed
        _table_cache_ts = time.time()
        print(f"[hamariweb] parsed {len(parsed)} rows")
    return _table_cache


def _find_row(table: dict, match_name: str) -> dict | None:
    """Find a stock row by partial, case-insensitive name match."""
    match_lower = match_name.lower()
    # Exact match first
    for name, row in table.items():
        if name.lower() == match_lower:
            return row
    # Then "starts with"
    for name, row in table.items():
        if name.lower().startswith(match_lower):
            return row
    # Then "contains"
    for name, row in table.items():
        if match_lower in name.lower():
            return row
    return None


def _build_quote_from_row(symbol: str, row: dict) -> dict:
    meta  = KNOWN_STOCKS[symbol]
    price = row["current"]
    prev  = row["ldcp"]
    chg   = round(row["change"], 2)
    chg_pct = round((chg / prev) * 100, 2) if prev else 0.0
    return {
        "symbol":       symbol,
        "company_name": meta["name"],
        "sector":       meta["sector"],
        "price":        round(price, 2),
        "open":         round(row["open"], 2),
        "high":         round(row["high"], 2),
        "low":          round(row["low"], 2),
        "prev_close":   round(prev, 2),
        "change":       chg,
        "change_pct":   chg_pct,
        "volume":       row["volume"],
        "last_updated": _now(),
        "source":       "hamariweb",
    }


# ── Mock fallback ──────────────────────────────────────────────────────────

def _mock_quote(symbol: str) -> dict:
    meta  = KNOWN_STOCKS.get(symbol, {"name": f"{symbol} Ltd.", "sector": "Unknown"})
    base  = BASE_PRICES.get(symbol, 200.0)
    seed  = int(datetime.now().strftime("%Y%m%d")) + abs(hash(symbol)) % 10000
    rng   = random.Random(seed)
    price = round(base * rng.uniform(0.97, 1.03), 2)
    prev  = round(base * rng.uniform(0.97, 1.03), 2)
    chg   = round(price - prev, 2)
    return {
        "symbol":       symbol,
        "company_name": meta["name"],
        "sector":       meta["sector"],
        "price":        price,
        "open":         round(prev * rng.uniform(0.998, 1.002), 2),
        "high":         round(max(price, prev) * rng.uniform(1.005, 1.015), 2),
        "low":          round(min(price, prev) * rng.uniform(0.985, 0.995), 2),
        "prev_close":   prev,
        "change":       chg,
        "change_pct":   round((chg / prev) * 100, 2) if prev else 0.0,
        "volume":       rng.randint(500_000, 9_000_000),
        "last_updated": _now(),
        "source":       "simulated",
    }


def _mock_history(symbol: str, period: str, anchor_price: float | None = None) -> list[dict]:
    base   = anchor_price or BASE_PRICES.get(symbol, 200.0)
    seed   = int(datetime.now().strftime("%Y%m%d")) + abs(hash(symbol + period)) % 10000
    rng    = random.Random(seed)
    counts = {"1D": 48, "1W": 35, "1M": 22, "3M": 60}
    n      = counts.get(period, 30)
    price  = base * rng.uniform(0.93, 1.07)
    points = []
    for i in range(n):
        price = round(price * rng.uniform(0.994, 1.006), 2)
        if period == "1D":
            label = f"{9 + i//12:02d}:{(i % 12)*5:02d}"
        elif period == "1W":
            label = (datetime.now() - timedelta(days=n - i)).strftime("%a %d")
        else:
            label = (datetime.now() - timedelta(days=n - i)).strftime("%b %d")
        points.append({"date": label, "price": price})
    if anchor_price:
        points[-1]["price"] = round(anchor_price, 2)
    return points


# ── Public API ─────────────────────────────────────────────────────────────

def get_stock_quote(symbol: str) -> dict:
    symbol = symbol.upper()
    cached = stock_cache.get(symbol)
    if cached:
        return cached

    meta  = KNOWN_STOCKS[symbol]
    table = _get_live_table()
    row   = _find_row(table, meta["match"]) if table else None

    data = _build_quote_from_row(symbol, row) if row else _mock_quote(symbol)
    stock_cache.set(symbol, data)
    return data


def get_all_quotes() -> list[dict]:
    _get_live_table()   # pre-warm: one HTTP request covers every symbol
    return [get_stock_quote(sym) for sym in KNOWN_STOCKS]


def get_stock_history(symbol: str, period: str) -> dict:
    """
    hamariweb's table is a live snapshot only — no history endpoint.
    History is simulated but anchored to today's real live price.
    """
    symbol    = symbol.upper()
    cache_key = f"history:{symbol}:{period}"
    cached    = stock_cache.get(cache_key)
    if cached:
        return cached

    quote  = get_stock_quote(symbol)
    anchor = quote["price"] if quote.get("source") == "hamariweb" else None
    points = _mock_history(symbol, period, anchor_price=anchor)

    result = {"symbol": symbol, "period": period, "data": points}
    stock_cache.set(cache_key, result)
    return result


def get_market_summary(quotes: list[dict] = None) -> dict:
    cache_key = "market:summary"
    cached    = stock_cache.get(cache_key)
    if cached:
        return cached

    if quotes is None:
        quotes = get_all_quotes()

    advancers = sum(1 for q in quotes if q["change_pct"] > 0)
    decliners = sum(1 for q in quotes if q["change_pct"] < 0)
    unchanged = len(quotes) - advancers - decliners
    total_vol = sum(q["volume"] for q in quotes)

    # Try to find KSE-100 index row in the live table
    table = _get_live_table()
    index_val = KSE100_BASE
    index_chg = 0.0
    index_pct = 0.0
    idx_row = None
    for name in ("KSE-100", "KSE 100", "PSX 100", "KSE100"):
        idx_row = _find_row(table, name)
        if idx_row:
            break

    if idx_row:
        index_val = round(idx_row["current"], 2)
        index_chg = round(idx_row["change"], 1)
        index_pct = round((index_chg / idx_row["ldcp"]) * 100, 2) if idx_row["ldcp"] else 0.0
    else:
        seed     = int(datetime.now().strftime("%Y%m%d"))
        rng      = random.Random(seed)
        prev_idx = index_val * rng.uniform(0.988, 1.012)
        index_chg = round(index_val - prev_idx, 1)
        index_pct = round((index_chg / prev_idx) * 100, 2) if prev_idx else 0.0

    summary = {
        "index_value":      index_val,
        "index_change":     index_chg,
        "index_change_pct": index_pct,
        "total_volume":     total_vol,
        "advancers":        advancers,
        "decliners":        decliners,
        "unchanged":        unchanged,
        "last_updated":     _now(),
    }
    stock_cache.set(cache_key, summary)
    return summary


def get_sector_weights() -> list[dict]:
    quotes = get_all_quotes()
    sector_changes: dict[str, list[float]] = {}
    for q in quotes:
        sector_changes.setdefault(q["sector"], []).append(q["change_pct"])
    result = []
    for row in SECTOR_DATA:
        changes = sector_changes.get(row["sector"], [0.0])
        avg_chg = round(sum(changes) / len(changes), 2)
        result.append({**row, "change_pct": avg_chg})
    return result