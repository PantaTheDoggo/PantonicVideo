from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


class SignalServiceImpl:
    def __init__(self, signal_component: object) -> None:
        self._comp = signal_component
        self._signals: dict[str, Any] = {}

    def signal_for_state(self, key: str) -> Any:
        if key not in self._signals:
            self._signals[key] = self._comp.make_signal(None, lambda _: None)
        return self._signals[key]

    def signal_for_path(self, path: Path) -> Any:
        k = str(path)
        if k not in self._signals:
            self._signals[k] = self._comp.make_signal(None, lambda _: None)
        return self._signals[k]

    def signal_for_plugins(self) -> Any:
        if "__plugins__" not in self._signals:
            self._signals["__plugins__"] = self._comp.make_signal([], lambda _: None)
        return self._signals["__plugins__"]

    def signal_for_alerts(self) -> Any:
        if "__alerts__" not in self._signals:
            self._signals["__alerts__"] = self._comp.make_signal([], lambda _: None)
        return self._signals["__alerts__"]

    def subscribe(self, signal: Any, callback: Callable) -> Any:
        return self._comp.subscribe(signal, callback)

    def unsubscribe(self, handle: Any) -> None:
        self._comp.unsubscribe(handle)
