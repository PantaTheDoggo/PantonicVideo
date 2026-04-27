from __future__ import annotations

from typing import Any


class AppStateServiceImpl:
    def __init__(self, app_state_component: object, signal_service: object) -> None:
        self._comp = app_state_component
        self._signal_service = signal_service

    def get(self, key: str) -> Any:
        return self._comp.state_get(key)

    def set(self, key: str, value: Any) -> None:
        self._comp.state_set(key, value)

    def delete(self, key: str) -> None:
        self._comp.state_delete(key)

    def observe(self, key: str) -> Any:
        return self._signal_service.signal_for_state(key)
