from __future__ import annotations

from pathlib import Path
from typing import Any


class FilesystemServiceImpl:
    def __init__(self, filesystem_component: object, signal_service: object) -> None:
        self._comp = filesystem_component
        self._signal_service = signal_service

    def read(self, path: Path) -> bytes:
        return self._comp.read_file(path)

    def write(self, path: Path, data: bytes) -> None:
        self._comp.write_file(path, data)

    def exists(self, path: Path) -> bool:
        return self._comp.exists(path)

    def delete(self, path: Path) -> None:
        self._comp.delete(path)

    def list(self, path: Path) -> list:
        return self._comp.list_dir(path)

    def make_dir(self, path: Path) -> None:
        self._comp.make_dir(path)

    def watch(self, path: Path) -> Any:
        return self._signal_service.signal_for_path(path)
