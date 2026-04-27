from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ImageFormat(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"


class CropRect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: int
    top: int
    width: int
    height: int


class Dimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int
    height: int
