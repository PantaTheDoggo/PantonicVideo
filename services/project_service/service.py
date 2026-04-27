from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from contracts.project import Project, ProjectMetadata

_METADATA_FILENAME = "pantonicvideo-project.json"


class ProjectServiceImpl:
    def __init__(
        self,
        app_state_service: object,
        filesystem_service: object,
        signal_service: object,
    ) -> None:
        self._app_state_service = app_state_service
        self._filesystem_service = filesystem_service
        self._signal_service = signal_service

    def get_current(self) -> Optional[Project]:
        path_str = self._app_state_service.get("project.path")
        if path_str is None:
            return None
        return Project(central_folder=Path(path_str))

    def set_current(self, folder: Path) -> None:
        folder = Path(folder)
        meta_file = folder / _METADATA_FILENAME
        if not self._filesystem_service.exists(meta_file):
            self._filesystem_service.write(
                meta_file, ProjectMetadata().model_dump_json().encode()
            )
        self._app_state_service.set("project.path", str(folder))

    def get_metadata(self) -> ProjectMetadata:
        path_str = self._app_state_service.get("project.path")
        if path_str is None:
            return ProjectMetadata()
        meta_file = Path(path_str) / _METADATA_FILENAME
        if not self._filesystem_service.exists(meta_file):
            return ProjectMetadata()
        raw = self._filesystem_service.read(meta_file)
        return ProjectMetadata.model_validate_json(raw)

    def update_metadata(self, updater: Callable[[ProjectMetadata], ProjectMetadata]) -> None:
        path_str = self._app_state_service.get("project.path")
        project_path = Path(path_str) if path_str else Path(".")
        meta_file = project_path / _METADATA_FILENAME
        if self._filesystem_service.exists(meta_file):
            raw = self._filesystem_service.read(meta_file)
            meta = ProjectMetadata.model_validate_json(raw)
        else:
            meta = ProjectMetadata()
        meta = updater(meta)
        self._filesystem_service.write(meta_file, meta.model_dump_json().encode())

    def observe_current(self) -> Any:
        return self._signal_service.signal_for_state("project.path")
