"""Tests for project_folder v1.0.0 — spec_project_folder_v1.0."""

import ast
import json
import uuid
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 required for plugin UI tests")

from PySide6.QtWidgets import QApplication, QMessageBox
from contracts.signals import SubscriptionHandle
from infracore.manifest.plugin_manifest import PluginManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    import sys
    return QApplication.instance() or QApplication(sys.argv[:1])


def _handle():
    return SubscriptionHandle(uuid.uuid4())


@pytest.fixture()
def tmp_project(tmp_path):
    root = tmp_path / "my_project"
    root.mkdir()
    (root / "notes.txt").write_bytes(b"")
    subdir = root / "assets"
    subdir.mkdir()
    return root


@pytest.fixture()
def services(tmp_project):
    from unittest.mock import MagicMock

    fs = MagicMock()
    fs.list_dir.return_value = [tmp_project / "notes.txt", tmp_project / "assets"]
    fs.watch.return_value = _handle()

    state = MagicMock()
    state.state_get.return_value = tmp_project
    state.state_observe.return_value = _handle()

    return {
        "app_state_service":  state,
        "filesystem_service": fs,
        "signal_service":     MagicMock(),
        "logging_service":    MagicMock(),
    }


@pytest.fixture()
def enabled_plugin(qapp, services):
    from plugins.project_folder.plugin import ProjectFolderPlugin
    plugin = ProjectFolderPlugin()
    plugin.on_load(services)
    plugin.on_enable()
    yield plugin, services
    plugin.on_disable()
    plugin.on_unload()


# ---------------------------------------------------------------------------
# 1. Manifest validation
# ---------------------------------------------------------------------------

class TestManifest:
    def test_manifest_validates_strict(self):
        """Manifest validates; extra field is rejected (G9)."""
        from pydantic import ValidationError
        data = json.loads(Path("plugins/project_folder/manifest.json").read_text())
        PluginManifest.model_validate(data)
        data["unexpected"] = "boom"
        with pytest.raises((ValidationError, TypeError)):
            PluginManifest.model_validate(data)

    def test_manifest_required_services(self):
        """4 services declared; filesystem_service.min_version == '1.1.0'."""
        data = json.loads(Path("plugins/project_folder/manifest.json").read_text())
        svcs = {s["name"]: s for s in data["required_services"]}
        assert "app_state_service"  in svcs
        assert "filesystem_service" in svcs
        assert "signal_service"     in svcs
        assert "logging_service"    in svcs
        assert svcs["filesystem_service"]["min_version"] == "1.1.0"


# ---------------------------------------------------------------------------
# 2. Lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_lifecycle_hooks_present(self, qapp, services):
        """4 lifecycle hooks are callable."""
        from plugins.project_folder.plugin import ProjectFolderPlugin
        p = ProjectFolderPlugin()
        for name in ("on_load", "on_enable", "on_disable", "on_unload"):
            assert callable(getattr(p, name, None))

    def test_lifecycle_order_clean(self, qapp, services):
        """load→enable→disable→unload completes without exception on a clean fixture."""
        from plugins.project_folder.plugin import ProjectFolderPlugin
        p = ProjectFolderPlugin()
        p.on_load(services)
        p.on_enable()
        p.on_disable()
        p.on_unload()


# ---------------------------------------------------------------------------
# 3. Empty state
# ---------------------------------------------------------------------------

class TestEmptyState:
    def test_empty_state_shows_placeholder(self, qapp, services):
        """When current_project is None, list_dir is not called and placeholder is visible."""
        from plugins.project_folder.plugin import ProjectFolderPlugin
        services["app_state_service"].state_get.return_value = None
        p = ProjectFolderPlugin()
        p.on_load(services)
        p.on_enable()
        services["filesystem_service"].list_dir.assert_not_called()
        assert not p._placeholder.isHidden()
        p.on_disable()
        p.on_unload()


# ---------------------------------------------------------------------------
# 4. Rendering & reactivity
# ---------------------------------------------------------------------------

class TestRendering:
    def test_initial_render_with_current_project(self, enabled_plugin, tmp_project):
        """Model is populated with items returned by list_dir on enable."""
        plugin, services = enabled_plugin
        services["filesystem_service"].list_dir.assert_called_with(tmp_project)
        assert plugin._model.rowCount() == 2

    def test_state_observe_subscribed_on_enable(self, enabled_plugin):
        """state_observe('current_project', ...) is called exactly once during on_enable."""
        plugin, services = enabled_plugin
        calls = [
            c for c in services["app_state_service"].state_observe.call_args_list
            if c.args[0] == "current_project"
        ]
        assert len(calls) == 1

    def test_state_change_re_renders(self, qapp, services, tmp_project):
        """When the state_observe callback fires with a new path, list_dir is called for that path."""
        from plugins.project_folder.plugin import ProjectFolderPlugin
        new_root = tmp_project.parent / "other_project"
        new_root.mkdir(exist_ok=True)
        services["filesystem_service"].list_dir.return_value = []
        p = ProjectFolderPlugin()
        p.on_load(services)
        p.on_enable()

        # capture the callback registered via state_observe
        observe_call = services["app_state_service"].state_observe.call_args
        callback = observe_call.args[1]
        callback(new_root)

        services["filesystem_service"].list_dir.assert_called_with(new_root)
        p.on_disable()
        p.on_unload()

    def test_watch_armed_on_enable_and_unwatched_on_disable(self, qapp, services, tmp_project):
        """watch is called on enable; unwatch is called symmetrically on disable."""
        from plugins.project_folder.plugin import ProjectFolderPlugin
        p = ProjectFolderPlugin()
        p.on_load(services)
        p.on_enable()
        assert services["filesystem_service"].watch.called
        handle = p._fs_h
        p.on_disable()
        services["filesystem_service"].unwatch.assert_called_with(handle)
        p.on_unload()

    def test_fs_event_triggers_re_render(self, enabled_plugin, tmp_project):
        """Delivering a FilesystemEvent to the watch callback causes list_dir to be called again."""
        from contracts.filesystem import FilesystemEvent
        from datetime import datetime, timezone
        plugin, services = enabled_plugin

        watch_call = services["filesystem_service"].watch.call_args
        fs_callback = watch_call.args[1]

        prev_count = services["filesystem_service"].list_dir.call_count
        event = FilesystemEvent(
            path=tmp_project / "notes.txt",
            kind="modified",
            timestamp=datetime.now(tz=timezone.utc),
        )
        fs_callback(event)
        assert services["filesystem_service"].list_dir.call_count > prev_count


# ---------------------------------------------------------------------------
# 5. Navigation
# ---------------------------------------------------------------------------

class TestNavigation:
    def test_double_click_folder_navigates(self, enabled_plugin, tmp_project):
        """Double-clicking a folder updates _cwd; state_set is NOT called."""
        plugin, services = enabled_plugin
        assets_path = tmp_project / "assets"
        # assets is index 1 in the model (list_dir returns [notes.txt, assets])
        idx = plugin._model.index(1, 0)
        plugin._on_double_click(idx)
        assert plugin._cwd == assets_path
        services["app_state_service"].state_set.assert_not_called()

    def test_double_click_file_emits_open_request(self, enabled_plugin, tmp_project):
        """Double-clicking a file calls state_set('open_file_request', path)."""
        plugin, services = enabled_plugin
        file_path = tmp_project / "notes.txt"
        idx = plugin._model.index(0, 0)
        plugin._on_double_click(idx)
        services["app_state_service"].state_set.assert_called_once_with("open_file_request", file_path)

    def test_backspace_clamped_at_root(self, enabled_plugin, tmp_project):
        """Backspace at current_project root is a no-op — no extra list_dir call."""
        plugin, services = enabled_plugin
        assert plugin._cwd == tmp_project
        prev_count = services["filesystem_service"].list_dir.call_count
        plugin._do_up()
        assert services["filesystem_service"].list_dir.call_count == prev_count

    def test_refresh_F5_calls_list_dir(self, enabled_plugin, tmp_project):
        """F5 / _do_refresh causes a new list_dir call for the current directory."""
        plugin, services = enabled_plugin
        prev_count = services["filesystem_service"].list_dir.call_count
        plugin._do_refresh()
        assert services["filesystem_service"].list_dir.call_count == prev_count + 1
        services["filesystem_service"].list_dir.assert_called_with(tmp_project)


# ---------------------------------------------------------------------------
# 6. CRUD operations
# ---------------------------------------------------------------------------

class TestCRUD:
    def _select_first(self, plugin):
        idx = plugin._model.index(0, 0)
        plugin._view.setCurrentIndex(idx)

    def test_delete_shortcut_with_confirmation(self, enabled_plugin, tmp_project, monkeypatch):
        """Delete with Yes confirmation calls filesystem_service.delete(path)."""
        plugin, services = enabled_plugin
        self._select_first(plugin)
        monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **kw: QMessageBox.Yes))
        plugin._do_delete()
        services["filesystem_service"].delete.assert_called_once_with(tmp_project / "notes.txt")

    def test_delete_shortcut_cancel_no_op(self, enabled_plugin, monkeypatch):
        """Delete with No confirmation does NOT call filesystem_service.delete."""
        plugin, services = enabled_plugin
        self._select_first(plugin)
        monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **kw: QMessageBox.No))
        plugin._do_delete()
        services["filesystem_service"].delete.assert_not_called()

    def test_rename_shortcut(self, enabled_plugin, tmp_project, monkeypatch):
        """F2 / _do_rename calls rename(src, src.parent / new_name)."""
        from PySide6.QtWidgets import QInputDialog
        plugin, services = enabled_plugin
        self._select_first(plugin)
        monkeypatch.setattr(
            QInputDialog, "getText",
            staticmethod(lambda *a, **kw: ("new_name.txt", True)),
        )
        plugin._do_rename()
        services["filesystem_service"].rename.assert_called_once_with(
            tmp_project / "notes.txt",
            tmp_project / "new_name.txt",
        )

    def test_cut_paste_calls_move(self, enabled_plugin, tmp_project):
        """Cut + Paste → filesystem_service.move(src, cwd/src.name)."""
        plugin, services = enabled_plugin
        self._select_first(plugin)
        plugin._do_cut()
        assert plugin._clipboard == (tmp_project / "notes.txt", "cut")
        plugin._do_paste()
        services["filesystem_service"].move.assert_called_once_with(
            tmp_project / "notes.txt",
            tmp_project / "notes.txt",
        )
        assert plugin._clipboard is None

    def test_copy_paste_calls_copy(self, enabled_plugin, tmp_project):
        """Copy + Paste → filesystem_service.copy(src, cwd/src.name)."""
        plugin, services = enabled_plugin
        self._select_first(plugin)
        plugin._do_copy()
        assert plugin._clipboard == (tmp_project / "notes.txt", "copy")
        plugin._do_paste()
        services["filesystem_service"].copy.assert_called_once_with(
            tmp_project / "notes.txt",
            tmp_project / "notes.txt",
        )

    def test_new_folder_shortcut(self, enabled_plugin, tmp_project, monkeypatch):
        """Ctrl+N → filesystem_service.make_dir(cwd / name)."""
        from PySide6.QtWidgets import QInputDialog
        plugin, services = enabled_plugin
        monkeypatch.setattr(
            QInputDialog, "getText",
            staticmethod(lambda *a, **kw: ("new_folder", True)),
        )
        plugin._do_new_folder()
        services["filesystem_service"].make_dir.assert_called_once_with(tmp_project / "new_folder")

    def test_new_file_shortcut(self, enabled_plugin, tmp_project, monkeypatch):
        """Ctrl+Shift+N → filesystem_service.write_file(cwd / name, b'')."""
        from PySide6.QtWidgets import QInputDialog
        plugin, services = enabled_plugin
        monkeypatch.setattr(
            QInputDialog, "getText",
            staticmethod(lambda *a, **kw: ("new_file.txt", True)),
        )
        plugin._do_new_file()
        services["filesystem_service"].write_file.assert_called_once_with(
            tmp_project / "new_file.txt", b""
        )


# ---------------------------------------------------------------------------
# 7. Failure containment (G8)
# ---------------------------------------------------------------------------

class TestFailureContainment:
    def test_failure_in_delete_raises_alert(self, enabled_plugin, tmp_project, monkeypatch):
        """IOError in delete → raise_alert('project_folder', ERROR, ...) without propagation."""
        from contracts.logging import LogLevel
        plugin, services = enabled_plugin
        idx = plugin._model.index(0, 0)
        plugin._view.setCurrentIndex(idx)
        monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **kw: QMessageBox.Yes))
        services["filesystem_service"].delete.side_effect = IOError("disk full")
        plugin._do_delete()  # must not propagate
        services["logging_service"].raise_alert.assert_called_once()
        call_args = services["logging_service"].raise_alert.call_args
        assert call_args.args[0] == "project_folder"
        assert call_args.args[1] == LogLevel.ERROR


# ---------------------------------------------------------------------------
# 8. Import constraints (G4)
# ---------------------------------------------------------------------------

class TestImports:
    def test_imports_allowlist_only(self):
        """AST scan: plugin imports zero symbols from infracore or services.*"""
        src = Path("plugins/project_folder/plugin.py").read_text()
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
