"""Tests for project_launcher plugin — §6.5, §6.1, §6.2."""

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 required for plugin UI tests")

from PySide6.QtWidgets import QApplication
from plugins.project_launcher.plugin import ProjectLauncherPlugin
from infracore.manifest.plugin_manifest import PluginManifest


@pytest.fixture(scope="module")
def qapp():
    import sys
    return QApplication.instance() or QApplication(sys.argv[:1])


@pytest.fixture()
def mocked_services():
    from unittest.mock import MagicMock
    return {
        "project_service": MagicMock(),
        "filesystem_service": MagicMock(),
        "logging_service": MagicMock(),
    }


class TestManifestValidation:
    """§6.1 — plugin manifest validates strictly (additionalProperties: false)."""

    def test_manifest_file_exists(self):
        """§6.1: plugins/project_launcher/manifest.json exists."""
        assert Path("plugins/project_launcher/manifest.json").exists()

    def test_manifest_validates(self):
        """§6.1: manifest validates under the authoritative PluginManifest schema."""
        data = json.loads(Path("plugins/project_launcher/manifest.json").read_text())
        manifest = PluginManifest.model_validate(data)
        assert manifest.name == "project_launcher"

    def test_manifest_required_services(self):
        """§6.5: project_launcher requires project_service, filesystem_service, logging_service."""
        data = json.loads(Path("plugins/project_launcher/manifest.json").read_text())
        svc_names = [s["name"] for s in data.get("required_services", [])]
        assert "project_service" in svc_names
        assert "filesystem_service" in svc_names
        assert "logging_service" in svc_names

    def test_manifest_rejects_extra_fields(self):
        """§6.1: PluginManifest rejects unknown fields."""
        from pydantic import ValidationError
        data = json.loads(Path("plugins/project_launcher/manifest.json").read_text())
        data["unknown_extra"] = "oops"
        with pytest.raises((ValidationError, TypeError)):
            PluginManifest.model_validate(data)


class TestLifecycleHooks:
    """§6.2 — on_load/on_enable/on_disable/on_unload called in correct order on a clean fixture."""

    def test_plugin_has_all_lifecycle_hooks(self, qapp):
        """§6.2: ProjectLauncherPlugin implements on_load, on_enable, on_disable, on_unload."""
        plugin = ProjectLauncherPlugin()
        assert callable(getattr(plugin, "on_load", None))
        assert callable(getattr(plugin, "on_enable", None))
        assert callable(getattr(plugin, "on_disable", None))
        assert callable(getattr(plugin, "on_unload", None))

    def test_on_load_does_not_raise(self, qapp, mocked_services):
        """§6.2: on_load completes without raising on a clean fixture."""
        plugin = ProjectLauncherPlugin()
        plugin.on_load(mocked_services)

    def test_on_enable_after_load_does_not_raise(self, qapp, mocked_services):
        """§6.2: on_enable completes without raising after on_load."""
        plugin = ProjectLauncherPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()

    def test_on_disable_after_enable_does_not_raise(self, qapp, mocked_services):
        """§6.2: on_disable completes without raising after on_enable."""
        plugin = ProjectLauncherPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        plugin.on_disable()

    def test_on_unload_after_disable_does_not_raise(self, qapp, mocked_services):
        """§6.2: on_unload completes without raising after on_disable."""
        plugin = ProjectLauncherPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        plugin.on_disable()
        plugin.on_unload()

    def test_lifecycle_order(self, qapp, mocked_services):
        """§6.2: full lifecycle sequence load→enable→disable→unload completes cleanly."""
        order = []
        plugin = ProjectLauncherPlugin()

        original_load = plugin.on_load
        original_enable = plugin.on_enable
        original_disable = plugin.on_disable
        original_unload = plugin.on_unload

        def patched_load(services):
            order.append("load")
            original_load(services)
        def patched_enable():
            order.append("enable")
            original_enable()
        def patched_disable():
            order.append("disable")
            original_disable()
        def patched_unload():
            order.append("unload")
            original_unload()

        plugin.on_load = patched_load
        plugin.on_enable = patched_enable
        plugin.on_disable = patched_disable
        plugin.on_unload = patched_unload

        plugin.on_load(mocked_services)
        plugin.on_enable()
        plugin.on_disable()
        plugin.on_unload()

        assert order == ["load", "enable", "disable", "unload"]


class TestOnCommit:
    """§6.5 — on commit calls ProjectService.set_current(folder)."""

    def test_commit_calls_set_current(self, qapp, mocked_services, tmp_path):
        """§6.5: when the user commits a folder, set_current is called on project_service."""
        plugin = ProjectLauncherPlugin()
        plugin.on_load(mocked_services)
        plugin.on_enable()
        plugin.commit(tmp_path)
        mocked_services["project_service"].set_current.assert_called_once_with(tmp_path)


class TestImportConstraints:
    """§10.1 — project_launcher must not import infracore or services directly."""

    def test_no_infracore_import(self):
        """§10.1: plugin source does not directly import from infracore."""
        import ast
        src = Path("plugins/project_launcher/plugin.py").read_text()
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
