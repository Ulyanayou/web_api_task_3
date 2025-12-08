import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws.manager import ws_manager

router = APIRouter()


@router.websocket("/ws/items")
async def ws_items(ws: WebSocket):
    await ws_manager.connect(ws)

    async def tick(): # Раз в 30 сек. шлем hello-сообщение
        while True:
            try:
                await ws.send_json({"type": "tick", "message": "hello"})
            except Exception:
                break
            await asyncio.sleep(30)

    tick_task = asyncio.create_task(tick())

    try:
        while True:
            try:
                msg = await ws.receive_text()
            except WebSocketDisconnect:
                break
            if msg == "ping": # Обработка входящих сообщений клиента
                try:
                    await ws.send_json({"type": "pong"})
                except Exception:
                    break
            elif msg == "close":
                break
            else: # Эхо-тест в JSON
                try: 
                    await ws.send_json({"type": "echo", "payload": msg})
                except Exception:
                    break
    finally:
        try:
            tick_task.cancel()
        except Exception:
            pass
        await ws_manager.disconnect(ws)
