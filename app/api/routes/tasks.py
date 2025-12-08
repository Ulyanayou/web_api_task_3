from fastapi import APIRouter
from app.tasks.monitor import start_background_monitor, run_monitor_cycle

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/run")
async def run_once():
    await run_monitor_cycle()
    return {"message": "Один цикл мониторинга выполнен"}


@router.post("/run/background")
async def run_background():
    msg = start_background_monitor()
    return {"message": msg}
