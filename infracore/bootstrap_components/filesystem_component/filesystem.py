from __future__ import annotations

import shutil
import threading
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from contracts.filesystem import FilesystemEvent
from contracts.signals import SubscriptionHandle

if TYPE_CHECKING:
    from infracore.bootstrap_components.signal_component.signal import SignalComponent

__component_version__ = "1.0.0"


class FilesystemComponent:
    def __init__(self, signal_component: Optional[object] = None) -> None:
        self._signal_component = signal_component
        self._path_locks: dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()
        self._watches: dict[uuid.UUID, tuple] = {}

    def _get_lock(self, path: Path) -> threading.Lock:
        key = str(Path(path).resolve())
        with self._locks_lock:
            if key not in self._path_locks:
                self._path_locks[key] = threading.Lock()
            return self._path_locks[key]

    def write_file(self, path: Path, data: bytes) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_lock(path):
            path.write_bytes(data)

    def read_file(self, path: Path) -> bytes:
        return Path(path).read_bytes()

    def exists(self, path: Path) -> bool:
        return Path(path).exists()

    def delete(self, path: Path) -> None:
        Path(path).unlink()

    def make_dir(self, path: Path, parents: bool = False) -> None:
        Path(path).mkdir(parents=parents, exist_ok=True)

    def list_dir(self, path: Path) -> list[Path]:
        return list(Path(path).iterdir())

    def watch(self, path: Path, callback: Callable) -> SubscriptionHandle:
        handle_id = uuid.uuid4()
        self._watches[handle_id] = (path, callback)
        return handle_id  # type: ignore[return-value]

    def unwatch(self, handle: SubscriptionHandle) -> None:
        self._watches.pop(handle, None)  # type: ignore[call-overload]

    def rename(self, src: Path, dst: Path) -> None:
        Path(src).rename(dst)

    def move(self, src: Path, dst: Path) -> None:
        shutil.move(str(src), dst)

    def copy(self, src: Path, dst: Path) -> None:
        shutil.copy2(src, dst)
