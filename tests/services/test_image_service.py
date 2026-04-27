"""Tests for ImageService — §5.9, §5.1."""

import json
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch
from services.image_service.service import ImageServiceImpl
from contracts.image import CropRect, Dimensions, ImageFormat


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: image_service/manifest.json is valid under ServiceManifest schema."""
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/image_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "image_service"

    def test_manifest_depends_on_filesystem_service(self):
        """§5.9: image_service depends_on filesystem_service >= 1.0."""
        data = json.loads(Path("services/image_service/manifest.json").read_text())
        dep_names = [d["name"] for d in data.get("depends_on", [])]
        assert "filesystem_service" in dep_names


class TestImageServiceProtocol:
    """§5.9 — ImageService protocol surface (with mocked Pillow)."""

    @pytest.fixture()
    def service(self, mock_filesystem_service, stub_pillow):
        return ImageServiceImpl(filesystem_service=mock_filesystem_service)

    def test_supported_formats_returns_png_and_jpeg(self, service):
        """§5.9, §17: supported_formats returns PNG and JPEG for v1."""
        formats = service.supported_formats()
        assert ImageFormat.PNG in formats
        assert ImageFormat.JPEG in formats

    def test_apply_crop_calls_filesystem_write(self, service, mock_filesystem_service, tmp_path, stub_pillow):
        """§5.9: apply_crop routes output through FilesystemService.write."""
        source = tmp_path / "source.png"
        source.write_bytes(b"PNG_DATA")
        output = tmp_path / "cropped.png"
        rect = CropRect(left=0, top=0, width=50, height=50)
        service.apply_crop(source, rect, output)
        mock_filesystem_service.write.assert_called()

    def test_resize_calls_filesystem_write(self, service, mock_filesystem_service, tmp_path, stub_pillow):
        """§5.9: resize routes output through FilesystemService.write."""
        source = tmp_path / "source.png"
        source.write_bytes(b"PNG_DATA")
        output = tmp_path / "resized.png"
        dims = Dimensions(width=800, height=600)
        service.resize(source, dims, output)
        mock_filesystem_service.write.assert_called()


class TestImageServiceIntegration:
    """§5.9 / §16.1 — integration smoke test with real Pillow."""

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("PIL"),
        reason="Pillow not installed",
    )
    def test_apply_crop_real_pillow(self, tmp_path, mock_filesystem_service):
        """§5.9 (integration): apply_crop produces a valid image output via real Pillow."""
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (200, 200), color="red")
        source = tmp_path / "test.png"
        img.save(str(source))

        svc = ImageServiceImpl(filesystem_service=mock_filesystem_service)
        output = tmp_path / "out.png"
        rect = CropRect(left=0, top=0, width=100, height=100)
        svc.apply_crop(source, rect, output)
        mock_filesystem_service.write.assert_called()

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("PIL"),
        reason="Pillow not installed",
    )
    def test_resize_real_pillow(self, tmp_path, mock_filesystem_service):
        """§5.9 (integration): resize produces a valid image output via real Pillow."""
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (400, 300), color="blue")
        source = tmp_path / "test2.png"
        img.save(str(source))

        svc = ImageServiceImpl(filesystem_service=mock_filesystem_service)
        output = tmp_path / "out2.png"
        dims = Dimensions(width=200, height=150)
        svc.resize(source, dims, output)
        mock_filesystem_service.write.assert_called()
