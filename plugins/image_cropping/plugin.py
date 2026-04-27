from __future__ import annotations

from pathlib import Path
from typing import Any

from contracts.image import CropRect, Dimensions


class ImageCroppingPlugin:
    """Image crop/resize plugin — §6.5. Qt renders the preview; no Pillow import."""

    def on_load(self, services: dict[str, Any]) -> None:
        self._image_service = services["image_service"]
        self._filesystem_service = services["filesystem_service"]
        self._project_service = services["project_service"]
        self._logging_service = services["logging_service"]

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def commit_crop(self, source: Path, rect: CropRect, output: Path) -> None:
        self._image_service.apply_crop(source, rect, output)

    def commit_resize(self, source: Path, dims: Dimensions, output: Path) -> None:
        self._image_service.resize(source, dims, output)
