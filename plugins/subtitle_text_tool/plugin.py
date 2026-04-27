from __future__ import annotations

from pathlib import Path
from typing import Any

from contracts.subtitle import SrtOptions


class SubtitleTextToolPlugin:
    """Text-to-SRT subtitle tool — §6.5."""

    def on_load(self, services: dict[str, Any]) -> None:
        self._subtitle_service = services["subtitle_service"]
        self._filesystem_service = services["filesystem_service"]
        self._project_service = services["project_service"]
        self._logging_service = services["logging_service"]

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def commit(self, text: str, destination: Path, opts: SrtOptions) -> None:
        self._subtitle_service.text_to_srt(text, destination, opts)
