from __future__ import annotations

import json
import logging as _stdlib_logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

STATE_WRITE_WARNING_WINDOW_MS = 50

# On Windows the default timer resolution is ~15ms, which makes the 50ms warning
# window test non-deterministic.  Force 1ms resolution for the process lifetime.
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)  # type: ignore[attr-defined]
    except Exception:
        pass

__component_version__ = "1.0.0"


class AppStateComponent:
    def __init__(
        self,
        signal_component: object,
        filesystem_component: object,
        logging_component: object,
        root: Path,
    ) -> None:
        self._signal = signal_component
        self._fs = filesystem_component
        self._log = logging_component
        self._root = Path(root)
        self._store: dict[str, Any] = {}
        self._observers: dict[str, dict[uuid.UUID, Callable]] = {}
        self._last_write_time: dict[str, float] = {}

    def load(self) -> None:
        state_file = self._root / "state.json"
        if not self._fs.exists(state_file):
            return
        try:
            raw = self._fs.read_file(state_file)
            self._store = json.loads(raw)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            corrupt_name = f"state.json.corrupt-{ts}"
            import os
            os.rename(state_file, self._root / corrupt_name)
            self._store = {}
            self._log.log("infracore", _stdlib_logging.WARNING,
                          f"state.json was corrupt; renamed to {corrupt_name}")

    def state_set(self, key: str, value: Any) -> None:
        now = time.perf_counter()
        if key in self._last_write_time:
            elapsed_ms = (now - self._last_write_time[key]) * 1000
            if elapsed_ms < STATE_WRITE_WARNING_WINDOW_MS:
                self._log.log(
                    "infracore",
                    _stdlib_logging.WARNING,
                    f"Rapid consecutive write to state key '{key}' "
                    f"({elapsed_ms:.1f}ms < {STATE_WRITE_WARNING_WINDOW_MS}ms)",
                )
        self._store[key] = value
        self._persist()
        # Record time AFTER persist so elapsed between consecutive calls equals the
        # wall-clock gap the caller controls (not inflated by our own I/O time).
        self._last_write_time[key] = time.perf_counter()
        for cb in list(self._observers.get(key, {}).values()):
            cb(value)

    def state_get(self, key: str) -> Any:
        return self._store.get(key)

    def state_delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._last_write_time.pop(key, None)
        self._persist()

    def state_observe(self, key: str, callback: Callable[[Any], None]) -> uuid.UUID:
        handle = uuid.uuid4()
        self._observers.setdefault(key, {})[handle] = callback
        return handle

    def state_unobserve(self, handle: uuid.UUID) -> None:
        for key_obs in self._observers.values():
            key_obs.pop(handle, None)

    def _persist(self) -> None:
        state_file = self._root / "state.json"
        self._fs.write_file(state_file, json.dumps(self._store).encode())
