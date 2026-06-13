# routers/ws.py
# WebSocket endpoint for live price updates.
#
# Instead of the frontend polling /stocks every 5 minutes, it opens
# one WebSocket connection and receives price updates pushed from
# the server every 15 seconds.
#
# Connect from JS:
#   const ws = new WebSocket("wss://yourapp.up.railway.app/ws/prices");
#   ws.onmessage = (event) => { const data = JSON.parse(event.data); ... }

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.psx_scraper import get_all_quotes, get_market_summary

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Tracks all currently-connected WebSocket clients."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)


manager = ConnectionManager()


@router.websocket("/ws/prices")
async def prices_ws(websocket: WebSocket):
    """
    WebSocket endpoint — pushes live quotes + market summary every 15 seconds.
    No authentication required (read-only public market data).
    """
    await manager.connect(websocket)
    try:
        while True:
            quotes  = get_all_quotes()
            summary = get_market_summary(quotes)
            payload = {
                "type": "price_update",
                "quotes": quotes,
                "summary": summary,
            }
            await websocket.send_json(payload)
            await asyncio.sleep(15)   # push every 15 seconds
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
