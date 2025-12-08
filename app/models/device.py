from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class DeviceBase(SQLModel):
    name: str
    address: str
    is_active: bool = True


class Device(DeviceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(SQLModel):
    name: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None