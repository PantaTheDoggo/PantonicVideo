from __future__ import annotations

import tempfile
from pathlib import Path

from contracts.image import CropRect, Dimensions, ImageFormat


class ImageServiceImpl:
    def __init__(self, filesystem_service: object) -> None:
        self._fs = filesystem_service

    def supported_formats(self) -> list[ImageFormat]:
        return [ImageFormat.PNG, ImageFormat.JPEG]

    def apply_crop(self, source: Path, rect: CropRect, output: Path) -> None:
        from PIL import Image as PILImage
        img = PILImage.open(source)
        box = (rect.left, rect.top, rect.left + rect.width, rect.top + rect.height)
        cropped = img.crop(box)
        data = self._save_to_bytes(cropped, output.suffix)
        self._fs.write(output, data)

    def resize(self, source: Path, dims: Dimensions, output: Path) -> None:
        from PIL import Image as PILImage
        img = PILImage.open(source)
        resized = img.resize((dims.width, dims.height), PILImage.LANCZOS)
        data = self._save_to_bytes(resized, output.suffix)
        self._fs.write(output, data)

    @staticmethod
    def _save_to_bytes(img: object, suffix: str) -> bytes:
        fmt = suffix.upper().lstrip(".")
        if fmt == "JPG":
            fmt = "JPEG"
        if not fmt:
            fmt = "PNG"
        with tempfile.NamedTemporaryFile(suffix=f".{fmt.lower()}", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            img.save(tmp_path, format=fmt)
            return tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)
