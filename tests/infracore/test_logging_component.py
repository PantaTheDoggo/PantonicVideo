"""Tests for LoggingComponent — §4.6, S8."""

import logging
from pathlib import Path

import pytest
from infracore.bootstrap_components.logging_component.logging import LoggingComponent
from infracore.bootstrap_components.filesystem_component.filesystem import (
    FilesystemComponent,
)


@pytest.fixture()
def log_component(tmp_path):
    fs = FilesystemComponent()
    return LoggingComponent(filesystem_component=fs, root=tmp_path)


class TestComponentVersion:
    """§4.1 — __component_version__ declared."""

    def test_component_version_declared(self):
        """§4.1: LoggingComponent module declares __component_version__ as semver."""
        import infracore.bootstrap_components.logging_component.logging as mod
        assert hasattr(mod, "__component_version__")
        v = mod.__component_version__
        parts = v.split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts)


class TestInfracoreLog:
    """§4.6 — rotating infracore log at <pantonicvideo-root>/logs/infracore.log."""

    def test_infracore_log_created(self, log_component, tmp_path):
        """§4.6: logging to 'infracore' writes to <root>/logs/infracore.log."""
        log_component.log("infracore", logging.INFO, "startup message")
        log_file = tmp_path / "logs" / "infracore.log"
        assert log_file.exists()


class TestPerPluginLogs:
    """§4.6, S8 — per-plugin logs at correct paths based on is_builtin."""

    def test_builtin_plugin_log_path(self, log_component, tmp_path):
        """S8: built-in plugin log is at <root>/logs/plugins/<name>/plugin.log."""
        log_component.log("my_builtin", logging.INFO, "test", is_builtin=True)
        log_file = tmp_path / "logs" / "plugins" / "my_builtin" / "plugin.log"
        assert log_file.exists()

    def test_third_party_plugin_log_path(self, log_component, tmp_path):
        """S8: third-party plugin log is at <root>/plugins/<name>/logs/plugin.log."""
        log_component.log("my_plugin", logging.INFO, "test", is_builtin=False)
        log_file = tmp_path / "plugins" / "my_plugin" / "logs" / "plugin.log"
        assert log_file.exists()

    def test_handler_created_lazily_on_first_log(self, log_component, tmp_path):
        """§4.6: per-plugin log handler is created on first log call, not at construction."""
        log_file = tmp_path / "logs" / "plugins" / "lazy_plugin" / "plugin.log"
        assert not log_file.exists()
        log_component.log("lazy_plugin", logging.INFO, "hello", is_builtin=True)
        assert log_file.exists()


class TestAlertSink:
    """§4.6 — alert sink with AlertEntry, observe_alerts, acknowledge."""

    def test_raise_alert_adds_entry(self, log_component):
        """§4.6: raise_alert adds an AlertEntry to the in-memory sink."""
        log_component.raise_alert("test_plugin", logging.WARNING, "something happened")
        alerts = log_component.list_alerts()
        assert len(alerts) == 1
        assert alerts[0].plugin == "test_plugin"
        assert alerts[0].summary == "something happened"
        assert alerts[0].acknowledged is False

    def test_acknowledge_sets_flag(self, log_component):
        """§4.6: acknowledge sets acknowledged=True on the matching entry."""
        log_component.raise_alert("plugin_a", logging.ERROR, "error occurred")
        alerts = log_component.list_alerts()
        ts = alerts[0].timestamp
        log_component.acknowledge(ts, "plugin_a")
        assert log_component.list_alerts()[0].acknowledged is True

    def test_observe_alerts_fires_on_raise(self, log_component):
        """§4.6: callback registered via observe_alerts fires when an alert is raised."""
        received = []
        log_component.observe_alerts(received.append)
        log_component.raise_alert("src", logging.WARNING, "msg")
        assert len(received) > 0

    def test_observe_alerts_fires_on_acknowledge(self, log_component):
        """§4.6: callback fires again after acknowledge re-emits the alert signal."""
        received = []
        log_component.raise_alert("src2", logging.ERROR, "err")
        log_component.observe_alerts(received.append)
        ts = log_component.list_alerts()[0].timestamp
        log_component.acknowledge(ts, "src2")
        assert len(received) >= 1

    @pytest.mark.parametrize(
        "level",
        [logging.WARNING, logging.ERROR, logging.CRITICAL],
    )
    def test_alert_levels(self, log_component, level):
        """§4.6, D9: alert entries are created with WARNING, ERROR, and CRITICAL levels."""
        log_component.raise_alert("lvl_plugin", level, "level test")
        alerts = log_component.list_alerts()
        found = [a for a in alerts if a.plugin == "lvl_plugin" and a.level == level]
        assert len(found) == 1
