from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class PluginStatus(str, Enum):
    loaded = "loaded"
    enabled = "enabled"
    disabled = "disabled"
    failed = "failed"


class PluginRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    author: str
    status: PluginStatus
    failure_reason: str | None
    is_builtin: bool
