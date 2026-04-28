"""Tests for project_launcher v1.1.0 — app_state integration and QFileDialog (spec_project_launcher_v1.1)."""

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
def services(tmp_path):
    from unittest.mock import MagicMock
    return {
        "project_service":    MagicMock(),
        "filesystem_service": MagicMock(),
        "app_state_service":  MagicMock(),
        "logging_service":    MagicMock(),
    }


def test_required_services_includes_app_state():
    """Manifest declares app_state_service as required."""
    data = json.loads(Path("plugins/project_launcher/manifest.json").read_text())
    svc_names = [s["name"] for s in data.get("required_services", [])]
    assert "app_state_service" in svc_names


def test_commit_writes_state_current_project(qapp, services, tmp_path):
    """commit() calls state_set('current_project', folder)."""
    plugin = ProjectLauncherPlugin()
    plugin.on_load(services)
    plugin.commit(tmp_path)
    services["app_state_service"].state_set.assert_called_once_with("current_project", tmp_path)


def test_commit_still_calls_set_current(qapp, services, tmp_path):
    """commit() still calls project_service.set_current(folder) — G2 regression guard."""
    plugin = ProjectLauncherPlugin()
    plugin.on_load(services)
    plugin.commit(tmp_path)
    services["project_service"].set_current.assert_called_once_with(tmp_path)


def test_on_enable_opens_dialog_and_commits(qapp, services, tmp_path, monkeypatch):
    """on_enable opens QFileDialog; if user selects a folder, commit is called."""
    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **kw: str(tmp_path)))
    plugin = ProjectLauncherPlugin()
    plugin.on_load(services)
    plugin.on_enable()
    services["project_service"].set_current.assert_called_once_with(tmp_path)
    services["app_state_service"].state_set.assert_called_once_with("current_project", tmp_path)


def test_on_enable_dialog_cancel_is_noop(qapp, services, monkeypatch):
    """on_enable is a no-op when dialog returns empty string (user cancelled)."""
    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **kw: ""))
    plugin = ProjectLauncherPlugin()
    plugin.on_load(services)
    plugin.on_enable()
    services["project_service"].set_current.assert_not_called()
    services["app_state_service"].state_set.assert_not_called()


def test_on_enable_not_reentrant(qapp, services, tmp_path, monkeypatch):
    """Re-entrant call to on_enable (from within the dialog event loop) is a no-op.

    QFileDialog.getExistingDirectory processes Qt events while the dialog is open.
    If on_enable is connected to a signal that fires during that event loop, a second
    call arrives before the first returns.  Without the guard this causes an infinite
    loop of dialogs.
    """
    from PySide6.QtWidgets import QFileDialog

    call_count = 0

    def fake_dialog(*a, **kw):
        nonlocal call_count
        call_count += 1
        # Simulate the plugin manager calling on_enable re-entrantly
        plugin.on_enable()
        return str(tmp_path)

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(fake_dialog))
    plugin = ProjectLauncherPlugin()
    plugin.on_load(services)
    plugin.on_enable()

    # dialog must have been opened exactly once despite re-entrant call
    assert call_count == 1
    services["project_service"].set_current.assert_called_once_with(tmp_path)


def test_imports_only_contracts_and_pyside6():
    """AST scan: plugin imports only contracts.*, PySide6.*, pathlib, typing — not infracore or services."""
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
            assert not module.startswith("infracore"), f"Forbidden import: {module}"
            assert not module.startswith("services."), f"Forbidden import: {module}"
