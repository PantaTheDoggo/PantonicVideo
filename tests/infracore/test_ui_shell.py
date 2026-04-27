"""Tests for the UI shell — §7."""

import pytest

pytest.importorskip("PySide6", reason="PySide6 required for UI tests")

from PySide6.QtWidgets import QApplication
from infracore.ui_shell.window import MainWindow
from infracore.ui_shell.docker_menu import DockerMenu
from infracore.ui_shell.alert_panel import AlertPanel


@pytest.fixture(scope="module")
def qapp():
    import sys
    app = QApplication.instance() or QApplication(sys.argv[:1])
    return app


class TestMainWindow:
    """§7.1 — QMainWindow with menus and status bar."""

    def test_main_window_is_qmainwindow(self, qapp):
        """§7.1: MainWindow is a QMainWindow subclass."""
        from PySide6.QtWidgets import QMainWindow
        window = MainWindow()
        assert isinstance(window, QMainWindow)

    def test_main_window_has_menu_bar(self, qapp):
        """§7.2: MainWindow has a non-None menu bar."""
        window = MainWindow()
        assert window.menuBar() is not None

    def test_main_window_has_status_bar(self, qapp):
        """§7.3: MainWindow has a non-None status bar."""
        window = MainWindow()
        assert window.statusBar() is not None


class TestDockerMenu:
    """§7.2 — Docker menu lists loaded/enabled/disabled plugins, hides failed ones."""

    def test_docker_menu_exists(self, qapp):
        """§7.2: DockerMenu can be instantiated."""
        menu = DockerMenu()
        assert menu is not None

    def test_failed_plugin_not_in_menu(self, qapp):
        """§7.2: plugins with status 'failed' are excluded from the Docker menu."""
        from infracore.bootstrap_components.plugin_registry_component.plugin_registry import (
            PluginRecord,
            PluginStatus,
        )
        failed_record = PluginRecord(
            name="broken",
            version="1.0.0",
            description="Broken",
            author="PantonicVideo",
            status=PluginStatus.failed,
            failure_reason="manifest invalid",
            is_builtin=True,
        )
        menu = DockerMenu()
        menu.update_plugins([failed_record])
        action_names = [a.text() for a in menu.actions()]
        assert "broken" not in action_names

    def test_loaded_plugin_in_menu(self, qapp):
        """§7.2: plugins with status 'loaded' appear in the Docker menu."""
        from infracore.bootstrap_components.plugin_registry_component.plugin_registry import (
            PluginRecord,
            PluginStatus,
        )
        loaded_record = PluginRecord(
            name="good_plugin",
            version="1.0.0",
            description="A good plugin.",
            author="PantonicVideo",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=True,
        )
        menu = DockerMenu()
        menu.update_plugins([loaded_record])
        action_names = [a.text() for a in menu.actions()]
        assert "good_plugin" in action_names

    def test_description_as_tooltip(self, qapp):
        """S15: each Docker menu entry shows the plugin description as a tooltip."""
        from infracore.bootstrap_components.plugin_registry_component.plugin_registry import (
            PluginRecord,
            PluginStatus,
        )
        record = PluginRecord(
            name="tip_plugin",
            version="1.0.0",
            description="Tooltip description.",
            author="PantonicVideo",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=True,
        )
        menu = DockerMenu()
        menu.update_plugins([record])
        actions = [a for a in menu.actions() if a.text() == "tip_plugin"]
        assert len(actions) == 1
        assert "Tooltip description." in actions[0].toolTip()


class TestAlertPanel:
    """§7.3, S14, S15 — status-bar alert icon and drill-in panel."""

    def test_alert_panel_quiescent_by_default(self, qapp):
        """§7.3: AlertPanel starts in the quiescent state (no unacknowledged alerts)."""
        panel = AlertPanel()
        assert panel.current_state() == "quiescent"

    @pytest.mark.parametrize(
        "level, expected_state",
        [
            (30, "warning"),   # logging.WARNING
            (40, "error"),     # logging.ERROR
            (50, "critical"),  # logging.CRITICAL
        ],
    )
    def test_alert_panel_state_by_level(self, qapp, level, expected_state):
        """§7.3: AlertPanel state reflects the highest unacknowledged alert level."""
        from contracts.logging import AlertEntry
        from datetime import datetime, timezone
        entry = AlertEntry(
            plugin="test_plugin",
            level=level,
            summary="something",
            timestamp=datetime.now(timezone.utc),
            acknowledged=False,
        )
        panel = AlertPanel()
        panel.update_alerts([entry])
        assert panel.current_state() == expected_state

    def test_alert_panel_rows_include_author(self, qapp):
        """S15: alert panel rows include the plugin's author field."""
        from contracts.logging import AlertEntry
        from datetime import datetime, timezone
        entry = AlertEntry(
            plugin="my_plugin",
            level=40,
            summary="An error occurred",
            timestamp=datetime.now(timezone.utc),
            acknowledged=False,
        )
        panel = AlertPanel()
        panel.update_alerts([entry], plugin_authors={"my_plugin": "PluginAuthorName"})
        assert panel.has_author_in_row("my_plugin", "PluginAuthorName")


class TestLayoutPersistence:
    """§7.4 — layout.json read/write and version mismatch fallback."""

    def test_save_and_restore_layout(self, qapp, tmp_path):
        """§7.4: layout is saved to <root>/layout.json and restored on next startup."""
        window = MainWindow()
        window.save_layout(tmp_path)
        layout_file = tmp_path / "layout.json"
        assert layout_file.exists()

        import json
        data = json.loads(layout_file.read_text())
        assert "version" in data
        assert "qt_state" in data

    def test_unrecognized_layout_version_falls_back(self, qapp, tmp_path):
        """S7: an unrecognized layout.json version triggers first-run fallback and WARNING log."""
        import json
        (tmp_path / "layout.json").write_text(
            json.dumps({"version": 9999, "qt_state": "", "saved_at": "2026-01-01T00:00:00Z"})
        )
        window = MainWindow()
        warnings = []
        window.restore_layout(tmp_path, on_warning=warnings.append)
        assert any("unrecognized" in w.lower() or "version" in w.lower() for w in warnings)
        renamed = list(tmp_path.glob("layout.json.unrecognized-*"))
        assert len(renamed) == 1

    def test_missing_layout_triggers_first_run(self, qapp, tmp_path):
        """§7.4: absent layout.json triggers the first-run layout."""
        window = MainWindow()
        warnings = []
        is_first_run = window.restore_layout(tmp_path, on_warning=warnings.append)
        assert is_first_run is True
