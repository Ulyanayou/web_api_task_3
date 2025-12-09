import asyncio
from typing import Optional
import time
import httpx
from sqlmodel import select

from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.check import CheckResult
from app.nats.client import publish_event
from app.ws.manager import ws_manager

# Глобальная ссылка на текущую фоновую задачу
_bg_task: Optional[asyncio.Task] = None

# Период мониторинга (в секундах)
MONITOR_PERIOD_SECONDS = 60

# Проверка доступности адреса HTTP-запросом и измерение задержки.
async def check_address(address: str) -> tuple[bool, Optional[float]]:
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(address)
            status_up = resp.status_code < 500
    except Exception:
        status_up = False
    latency_ms = (time.perf_counter() - start) * 1000.0
    return status_up, latency_ms


# Один цикл мониторинга
async def run_monitor_cycle():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Device).where(Device.is_active == True))
        devices = result.scalars().all()
        for d in devices:
            try:
                status_up, latency_ms = await check_address(d.address)
                check = CheckResult(device_id=d.id, status_up=status_up, latency_ms=latency_ms)
                session.add(check)
                # Рассылаем отдельный результат проверки в WebSocket-клиенты
                # Формат: {"type": "check.created", "payload": <данные проверки>}
                try:
                    await ws_manager.broadcast_json({
                        "type": "check.created",
                        "payload": {
                            "device_id": d.id,
                            "status_up": status_up,
                            "latency_ms": latency_ms,
                        }
                    })
                except Exception:
                    # Если отправка по WS не удалась, продолжаем цикл
                    pass
            except Exception:
                # Продолжаем другие устройства даже при ошибке
                continue
        await session.commit()

        event = {"type": "monitor.cycle.finished", "payload": {"devices_checked": len(devices)}}
        if not await publish_event(event):
            await ws_manager.broadcast_json(event)


async def monitor_loop():
    while True:
        try:
            await run_monitor_cycle()
        except Exception as e:
            print(f"monitor: error — {e}")
        await asyncio.sleep(MONITOR_PERIOD_SECONDS)


def start_background_monitor() -> str:
    global _bg_task
    loop = asyncio.get_event_loop()
    if _bg_task and not _bg_task.done():
        return "Фоновый мониторинг уже запущен"
    _bg_task = loop.create_task(monitor_loop())
    return "Фоновый мониторинг запущен"
