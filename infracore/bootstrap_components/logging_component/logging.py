from __future__ import annotations

import logging as _stdlib_logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from contracts.logging import AlertEntry

if TYPE_CHECKING:
    from infracore.bootstrap_components.filesystem_component.filesystem import FilesystemComponent

__component_version__ = "1.0.0"

# stdlib logging writes directly to files — this is the documented G6 exception.


class LoggingComponent:
    def __init__(
        self,
        filesystem_component: object,
        root: Path,
    ) -> None:
        self._fs = filesystem_component
        self._root = Path(root)
        self._loggers: dict[str, _stdlib_logging.Logger] = {}
        self._alerts: list[AlertEntry] = []
        self._alert_observers: dict[uuid.UUID, Callable] = {}
        self._warning_buffer: list[str] = []
        self._error_buffer: list[str] = []

    def _log_path(self, channel: str, is_builtin: bool) -> Path:
        if channel == "infracore":
            return self._root / "logs" / "infracore.log"
        if is_builtin:
            return self._root / "logs" / "plugins" / channel / "plugin.log"
        return self._root / "plugins" / channel / "logs" / "plugin.log"

    def _get_logger(self, channel: str, is_builtin: bool) -> _stdlib_logging.Logger:
        key = f"{channel}:{is_builtin}"
        if key in self._loggers:
            return self._loggers[key]
        log_path = self._log_path(channel, is_builtin)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger = _stdlib_logging.getLogger(f"pantonicvideo.{key}.{uuid.uuid4().hex[:8]}")
        logger.setLevel(_stdlib_logging.DEBUG)
        handler = _stdlib_logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(_stdlib_logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        self._loggers[key] = logger
        return logger

    def log(self, channel: str, level: int, message: str, is_builtin: bool = True) -> None:
        logger = self._get_logger(channel, is_builtin)
        logger.log(level, message)
        if level >= _stdlib_logging.WARNING:
            self._warning_buffer.append(message)
        if level >= _stdlib_logging.ERROR:
            self._error_buffer.append(message)

    def captured_warnings(self) -> list[str]:
        return list(self._warning_buffer)

    def captured_errors(self) -> list[str]:
        return list(self._error_buffer)

    def raise_alert(self, plugin: str, level: int, summary: str) -> None:
        entry = AlertEntry(
            plugin=plugin,
            level=level,
            summary=summary,
            timestamp=datetime.now(timezone.utc),
            acknowledged=False,
        )
        self._alerts.append(entry)
        self._notify_observers()

    def list_alerts(self) -> list[AlertEntry]:
        return list(self._alerts)

    def acknowledge(self, timestamp: datetime, plugin: str) -> None:
        for i, alert in enumerate(self._alerts):
            if alert.timestamp == timestamp and alert.plugin == plugin:
                self._alerts[i] = alert.model_copy(update={"acknowledged": True})
                break
        self._notify_observers()

    def observe_alerts(self, callback: Callable) -> uuid.UUID:
        handle = uuid.uuid4()
        self._alert_observers[handle] = callback
        return handle

    def _notify_observers(self) -> None:
        snapshot = list(self._alerts)
        for cb in list(self._alert_observers.values()):
            cb(snapshot)
