from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class CheckResultBase(SQLModel):
    status_up: bool
    latency_ms: Optional[float] = None


class CheckResult(CheckResultBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="device.id")
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class CheckCreate(CheckResultBase):
    pass
