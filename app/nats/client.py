import json
import nats
from app.ws.manager import ws_manager

NATS_URL = "nats://127.0.0.1:4222"
SUBJECT = "items.updates"

# глобальное подключение NATS
connection = None
is_connected = False

async def connect_nats():
    global connection, is_connected

    try:
        connection = await nats.connect(NATS_URL, connect_timeout=2)
        is_connected = True
        print("NATS: connected")

        async def handler(msg):
            try:
                data = json.loads(msg.data.decode())
            except Exception:
                data = {"type": "unknown", "raw": msg.data.decode(errors="ignore")}
            # Логируем и рассылаем всем WebSocket-клиентам
            print("NATS inbound:", data)
            try:
                await ws_manager.broadcast_json({"type": "nats.inbound", "payload": data})
            except Exception:
                pass

        await connection.subscribe(SUBJECT, cb=handler) # Подписывает клиент на subject items.updates
        return True
    except Exception as e:
        print(f"NATS: не удалось подключиться ({e}). Продолжаем без NATS.")
        is_connected = False
        connection = None
        return False


async def close_nats():
    global connection, is_connected
    if connection is not None:
        try:
            await connection.drain() # корректно закрыть соединение
        except Exception:
            pass
    connection = None
    is_connected = False


async def publish_event(event: dict):
    """Публикация события в NATS. Если соединения нет — вернёт False."""
    if not is_connected or connection is None:
        return False
    try:
        # асинхронно публикуем сообщение в канал SUBJECT
        await connection.publish(SUBJECT, json.dumps(event, default=str).encode())
        return True
    except Exception as e:
        print(f"NATS publish error: {e}")
        return False
