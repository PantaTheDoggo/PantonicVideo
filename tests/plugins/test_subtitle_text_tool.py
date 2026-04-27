"""Tests for subtitle_text_tool plugin — §6.5, §6.1, §6.2."""

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 required for plugin UI tests")

from PySide6.QtWidgets import QApplication
from plugins.subtitle_text_tool.plugin import SubtitleTextToolPlugin
from infracore.manifest.plugin_manifest import PluginManifest


@pytest.fixture(scope="module")
def qapp():
    import sys
    return QApplication.instance() or QApplication(sys.argv[:1])


@pytest.fixture()
def mocked_services():
    from unittest.mock import MagicMock
    return {
        "subtitle_service": MagicMock(),
        "filesystem_service": MagicMock(),
        "project_service": MagicMock(),
        "logging_service": MagicMock(),
    }


class TestManifestValidation:
    """§6.1 — plugin manifest validates strictly."""

    def test_manifest_file_exists(self):
        """§6.1: plugins/subtitle_text_tool/manifest.json exists."""
        assert Path("plugins/subtitle_text_tool/manifest.json").exists()

    def test_manifest_validates(self):
        """§6.1: manifest validates under PluginManifest schema."""
        data = json.loads(Path("plugins/subtitle_text_tool/manifest.json").read_text())
        manifest = PluginManifest.model_validate(data)
        assert manifest.name == "subtitle_text_tool"

    def test_manifest_required_services(self):
        """§6.5: subtitle_text_tool requires subtitle_service, filesystem_service, project_service, logging_service."""
        data = json.loads(Path("plugins/subtitle_text_tool/manifest.json").read_text())
        svc_names = [s["name"] for s in data.get("required_services", [])]
        assert "subtitle_service" in svc_names
        assert "filesystem_service" in svc_names
        assert "project_service" in svc_names
        assert "logging_service" in svc_names

    def test_manifest_rejects_extra_fields(self):
        """§6.1: PluginManifest rejects unknown fields."""
        from pydantic import ValidationError
        data = json.loads(Path("plugins/subtitle_text_tool/manifest.json").read_text())
        data["extra_field"] = "bad"
        with pytest.raises((ValidationError, TypeError)):
            PluginManifest.model_validate(data)


class TestLifecycleHooks:
    """§6.2 — lifecycle hooks complete cleanly on a clean fixture."""

    def test_plugin_has_all_lifecycle_hooks(self, qapp):
        """§6.2: SubtitleTextToolPlugin implements on_load, on_enable, on_disable, on_unload."""
        plugin = SubtitleTextToolPlugin()
        for hook in ("on_load", "on_enable", "on_disable", "on_unload"):
            assert callable(getattr(plugin, hook, None))

    def test_lifecycle_sequence_completes_without_exception(self, qapp, mocked_services):
        """§6.2: full lifecycle sequence on SubtitleTextToolPlugin completes without raising."""
        plugin = SubtitleTextToolPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        plugin.on_disable()
        plugin.on_unload()


class TestOnCommit:
    """§6.5 — commit calls SubtitleService.text_to_srt."""

    def test_commit_calls_text_to_srt(self, qapp, mocked_services, tmp_path):
        """§6.5: commit calls subtitle_service.text_to_srt with user text and destination."""
        from contracts.subtitle import SrtOptions
        plugin = SubtitleTextToolPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        output = tmp_path / "output.srt"
        opts = SrtOptions()
        plugin.commit("Hello subtitle text.", output, opts)
        mocked_services["subtitle_service"].text_to_srt.assert_called_once_with(
            "Hello subtitle text.", output, opts
        )

    def test_commit_with_custom_pacing(self, qapp, mocked_services, tmp_path):
        """§6.5: commit passes custom SrtOptions pacing controls to subtitle_service."""
        from contracts.subtitle import SrtOptions
        plugin = SubtitleTextToolPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        output = tmp_path / "paced.srt"
        opts = SrtOptions(cps=10, max_line_chars=30)
        plugin.commit("Text with custom pacing.", output, opts)
        call_opts = mocked_services["subtitle_service"].text_to_srt.call_args[0][2]
        assert call_opts.cps == 10
        assert call_opts.max_line_chars == 30


class TestImportConstraints:
    """§10.1 — subtitle_text_tool must not import infracore or services."""

    def test_no_infracore_or_services_import(self):
        """§10.1: plugin source imports only from contracts and PySide6."""
        import ast
        src = Path("plugins/subtitle_text_tool/plugin.py").read_text()
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
