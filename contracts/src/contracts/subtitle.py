from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SrtOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cps: int = 17
    max_line_chars: int = 42
    min_duration_ms: int = 1000
    gap_ms: int = 100
