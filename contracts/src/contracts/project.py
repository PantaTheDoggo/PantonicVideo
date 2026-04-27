from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    central_folder: Path


class ProjectMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_source_folders: list[Path] = []
    audio_source_folders: list[Path] = []
