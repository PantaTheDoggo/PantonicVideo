from __future__ import annotations

from pathlib import Path
from typing import Any


class ProjectLauncherPlugin:
    """Folder picker plugin — §6.5. Auto-enabled on first run (§7.5)."""

    def on_load(self, services: dict[str, Any]) -> None:
        self._project_service = services["project_service"]
        self._filesystem_service = services["filesystem_service"]
        self._logging_service = services["logging_service"]

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def commit(self, folder: Path) -> None:
        self._project_service.set_current(folder)
