from __future__ import annotations

from typing import Any, Protocol


class InjectorService(Protocol):
    def resolve(self, name: str, min_version: str) -> Any: ...
