from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog


class ProjectLauncherPlugin:
    def on_load(self, services: dict[str, Any]) -> None:
        self._project_service    = services["project_service"]
        self._filesystem_service = services["filesystem_service"]
        self._app_state_service  = services["app_state_service"]
        self._logging_service    = services["logging_service"]
        self._dialog_active      = False

    def on_enable(self) -> None:
        # QFileDialog runs a local event loop; guard prevents re-entrant calls
        if self._dialog_active:
            return
        self._dialog_active = True
        try:
            selected = QFileDialog.getExistingDirectory(
                None, "Open Folder", "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )
            if selected:
                self.commit(Path(selected))
        finally:
            self._dialog_active = False

    def on_disable(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def commit(self, folder: Path) -> None:
        self._project_service.set_current(folder)
        self._app_state_service.state_set("current_project", folder)
