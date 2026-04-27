from __future__ import annotations

import logging as _logging
from datetime import datetime
from enum import IntEnum
from typing import Callable, Protocol

from pydantic import BaseModel, ConfigDict


class LogLevel(IntEnum):
    WARNING = _logging.WARNING
    ERROR = _logging.ERROR
    CRITICAL = _logging.CRITICAL


class AlertEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str
    level: int
    summary: str
    timestamp: datetime
    acknowledged: bool = False


class LoggingService(Protocol):
    def log(self, channel: str, level: int, message: str, *, is_builtin: bool = True) -> None: ...
    def raise_alert(self, plugin: str, level: int, summary: str) -> None: ...
    def list_alerts(self) -> list[AlertEntry]: ...
    def acknowledge(self, timestamp: datetime, plugin: str) -> None: ...
    def observe_alerts(self, callback: Callable[[list[AlertEntry]], None]) -> object: ...
