from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Literal, Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from contracts.signals import SubscriptionHandle


class FilesystemEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    kind: Literal["created", "modified", "deleted"]
    timestamp: datetime


class FilesystemService(Protocol):
    def write_file(self, path: Path, data: bytes) -> None: ...
    def read_file(self, path: Path) -> bytes: ...
    def exists(self, path: Path) -> bool: ...
    def delete(self, path: Path) -> None: ...
    def make_dir(self, path: Path, *, parents: bool = False) -> None: ...
    def list_dir(self, path: Path) -> list[Path]: ...
    def watch(self, path: Path, callback: Callable[[FilesystemEvent], None]) -> SubscriptionHandle: ...
    def unwatch(self, handle: SubscriptionHandle) -> None: ...
