from __future__ import annotations

import uuid
from typing import Callable

from contracts.plugin_registry import PluginRecord, PluginStatus

__component_version__ = "1.0.0"


class PluginRegistryComponent:
    def __init__(
        self,
        signal_component: object,
        filesystem_component: object,
        app_state_component: object,
        logging_component: object,
    ) -> None:
        self._signal = signal_component
        self._fs = filesystem_component
        self._state = app_state_component
        self._log = logging_component
        self._records: list[PluginRecord] = []
        self._observers: dict[uuid.UUID, Callable] = {}

    def _record_loaded(self, record: PluginRecord) -> None:
        self._records.append(record)
        self._notify_observers()

    def _record_failed(self, name: str, reason: str) -> None:
        existing = next((r for r in self._records if r.name == name and r.is_builtin), None)
        if existing is None:
            record = PluginRecord(
                name=name,
                version="",
                description="",
                author="",
                status=PluginStatus.failed,
                failure_reason=reason,
                is_builtin=False,
            )
            self._records.append(record)
        self._notify_observers()

    def _set_enabled(self, name: str, enabled: bool) -> None:
        new_status = PluginStatus.enabled if enabled else PluginStatus.disabled
        self._records = [
            r.model_copy(update={"status": new_status})
            if r.name == name and r.status != PluginStatus.failed
            else r
            for r in self._records
        ]
        self._notify_observers()

    def list_plugins(self) -> list[PluginRecord]:
        return list(self._records)

    def observe_plugins(self, callback: Callable) -> uuid.UUID:
        handle = uuid.uuid4()
        self._observers[handle] = callback
        return handle

    def unobserve_plugins(self, handle: uuid.UUID) -> None:
        self._observers.pop(handle, None)

    def _notify_observers(self) -> None:
        snapshot = list(self._records)
        for cb in list(self._observers.values()):
            cb(snapshot)
