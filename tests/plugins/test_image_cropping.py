"""Tests for image_cropping plugin — §6.5, §6.1, §6.2."""

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 required for plugin UI tests")

from PySide6.QtWidgets import QApplication
from plugins.image_cropping.plugin import ImageCroppingPlugin
from infracore.manifest.plugin_manifest import PluginManifest


@pytest.fixture(scope="module")
def qapp():
    import sys
    return QApplication.instance() or QApplication(sys.argv[:1])


@pytest.fixture()
def mocked_services():
    from unittest.mock import MagicMock
    return {
        "image_service": MagicMock(),
        "filesystem_service": MagicMock(),
        "project_service": MagicMock(),
        "logging_service": MagicMock(),
    }


class TestManifestValidation:
    """§6.1 — plugin manifest validates strictly."""

    def test_manifest_file_exists(self):
        """§6.1: plugins/image_cropping/manifest.json exists."""
        assert Path("plugins/image_cropping/manifest.json").exists()

    def test_manifest_validates(self):
        """§6.1: manifest validates under PluginManifest schema."""
        data = json.loads(Path("plugins/image_cropping/manifest.json").read_text())
        manifest = PluginManifest.model_validate(data)
        assert manifest.name == "image_cropping"

    def test_manifest_required_services(self):
        """§6.5: image_cropping requires image_service, filesystem_service, project_service, logging_service."""
        data = json.loads(Path("plugins/image_cropping/manifest.json").read_text())
        svc_names = [s["name"] for s in data.get("required_services", [])]
        assert "image_service" in svc_names
        assert "filesystem_service" in svc_names
        assert "project_service" in svc_names
        assert "logging_service" in svc_names

    def test_manifest_rejects_extra_fields(self):
        """§6.1: PluginManifest rejects unknown fields (additionalProperties: false)."""
        from pydantic import ValidationError
        data = json.loads(Path("plugins/image_cropping/manifest.json").read_text())
        data["bad_field"] = "oops"
        with pytest.raises((ValidationError, TypeError)):
            PluginManifest.model_validate(data)


class TestLifecycleHooks:
    """§6.2 — lifecycle hooks complete cleanly on a clean fixture."""

    def test_plugin_has_all_lifecycle_hooks(self, qapp):
        """§6.2: ImageCroppingPlugin implements on_load, on_enable, on_disable, on_unload."""
        plugin = ImageCroppingPlugin()
        for hook in ("on_load", "on_enable", "on_disable", "on_unload"):
            assert callable(getattr(plugin, hook, None))

    def test_lifecycle_sequence_completes_without_exception(self, qapp, mocked_services):
        """§6.2: full lifecycle sequence on ImageCroppingPlugin completes without raising."""
        plugin = ImageCroppingPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        plugin.on_disable()
        plugin.on_unload()


class TestOnCommit:
    """§6.5 — commit calls ImageService.apply_crop or ImageService.resize."""

    def test_commit_crop_calls_apply_crop(self, qapp, mocked_services, tmp_path):
        """§6.5: commit with crop operation calls image_service.apply_crop."""
        from contracts.image import CropRect
        plugin = ImageCroppingPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        source = tmp_path / "input.png"
        source.write_bytes(b"PNG")
        output = tmp_path / "output.png"
        rect = CropRect(left=0, top=0, width=50, height=50)
        plugin.commit_crop(source, rect, output)
        mocked_services["image_service"].apply_crop.assert_called_once_with(source, rect, output)

    def test_commit_resize_calls_resize(self, qapp, mocked_services, tmp_path):
        """§6.5: commit with resize operation calls image_service.resize."""
        from contracts.image import Dimensions
        plugin = ImageCroppingPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        source = tmp_path / "input2.png"
        source.write_bytes(b"PNG")
        output = tmp_path / "output2.png"
        dims = Dimensions(width=800, height=600)
        plugin.commit_resize(source, dims, output)
        mocked_services["image_service"].resize.assert_called_once_with(source, dims, output)


class TestNoPillowImport:
    """§6.4 — image_cropping must not import Pillow (preview is Qt-rendered, §6.5)."""

    def test_no_pillow_import_in_plugin(self):
        """§6.5: image_cropping plugin does not import PIL/Pillow directly."""
        import ast
        src = Path("plugins/image_cropping/plugin.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    module = ",".join(alias.name for alias in node.names)
                assert not module.startswith("PIL"), (
                    "image_cropping plugin must not import PIL/Pillow directly"
                )


class TestImportConstraints:
    """§10.1 — image_cropping must not import infracore or services."""

    def test_no_infracore_or_services_import(self):
        """§10.1: plugin source imports only from contracts and PySide6."""
        import ast
        src = Path("plugins/image_cropping/plugin.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    module = ",".join(alias.name for alias in node.names)
                assert not module.startswith("infracore"), (
                    f"Plugin imports from infracore: {module}"
                )
                assert not module.startswith("services."), (
                    f"Plugin imports from services: {module}"
                )
