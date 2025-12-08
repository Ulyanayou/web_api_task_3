import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.config import settings
from app.db.session import engine

from app.api.routes.devices import router as devices_router
from app.api.routes.tasks import router as tasks_router
from app.ws.items import router as ws_items_router
from app.nats.client import connect_nats, close_nats
from app.tasks.monitor import start_background_monitor

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/swagger",
    description="Мониторинг устройств: REST API",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    await connect_nats() # Подключаемся к NATS и подписываемся

    # Автозапуск фонового мониторинга при старте приложения
    # start_background_monitor()


@app.on_event("shutdown")
async def on_shutdown():
    await close_nats()


app.include_router(devices_router)
app.include_router(tasks_router)
app.include_router(ws_items_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)
