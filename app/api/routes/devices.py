from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db.session import get_db
from app.models.device import Device, DeviceCreate, DeviceUpdate
from app.models.check import CheckResult, CheckCreate
from app.nats.client import publish_event
from app.ws.manager import ws_manager

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("/", response_model=List[Device])
async def list_devices(
    is_active: Optional[bool] = Query(default=None), # необязательный параметр
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Device)
    if is_active is not None: # если фильтр задан
        stmt = stmt.where(Device.is_active == is_active)
    result = await db.execute(stmt.order_by(Device.id))
    return result.scalars().all()


@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/", response_model=Device, status_code=201)
async def create_device(item: DeviceCreate, db: AsyncSession = Depends(get_db)):
    device = Device(**item.dict()) # создание модели из схемы
    db.add(device)
    await db.commit()
    await db.refresh(device)

    event = {"type": "device.created", "payload": device.dict()}
    if not await publish_event(event):
        await ws_manager.broadcast_json(event)
    return device


@router.patch("/{device_id}", response_model=Device)
async def update_device(
    device_id: int, item: DeviceUpdate, db: AsyncSession = Depends(get_db)
):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    data = item.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(device, k, v)
    db.add(device)
    await db.commit()
    await db.refresh(device)

    event = {"type": "device.updated", "payload": device.dict()}
    if not await publish_event(event):
        await ws_manager.broadcast_json(event)
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.delete(device)
    await db.commit()

    event = {"type": "device.deleted", "payload": {"id": device_id}}
    if not await publish_event(event):
        await ws_manager.broadcast_json(event)


@router.get("/{device_id}/checks", response_model=List[CheckResult])
async def list_device_checks(
    device_id: int,
    limit: int = Query(50, ge=1, le=200), # ограничение количества результатов
    db: AsyncSession = Depends(get_db),
):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    stmt = (
        select(CheckResult)
        .where(CheckResult.device_id == device_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
