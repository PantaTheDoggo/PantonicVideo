"""Tests for AppStateComponent — §4.4, S12."""

import time
import threading
from pathlib import Path

import pytest
from infracore.bootstrap_components.app_state_component.app_state import (
    AppStateComponent,
    STATE_WRITE_WARNING_WINDOW_MS,
)
from infracore.bootstrap_components.signal_component.signal import SignalComponent
from infracore.bootstrap_components.filesystem_component.filesystem import (
    FilesystemComponent,
)
from infracore.bootstrap_components.logging_component.logging import LoggingComponent


class TestComponentVersion:
    """§4.1 — __component_version__ declared."""

    def test_component_version_declared(self):
        """§4.1: AppStateComponent module declares __component_version__ as semver."""
        import infracore.bootstrap_components.app_state_component.app_state as mod
        assert hasattr(mod, "__component_version__")
        v = mod.__component_version__
        parts = v.split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts)


class TestWriteWarningWindowConstant:
    """S12 — STATE_WRITE_WARNING_WINDOW_MS is a module-level constant of 50."""

    def test_warning_window_value(self):
        """S12: STATE_WRITE_WARNING_WINDOW_MS equals 50 and is not user-configurable."""
        assert STATE_WRITE_WARNING_WINDOW_MS == 50


class TestBasicOperations:
    """§4.4 — get/set/delete/observe round-trips."""

    @pytest.fixture()
    def component(self, tmp_path):
        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        return AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )

    def test_set_and_get(self, component):
        """§4.4: state_set followed by state_get returns the stored value."""
        component.state_set("k", "v")
        assert component.state_get("k") == "v"

    def test_get_missing_returns_none(self, component):
        """§4.4: state_get on an unset key returns None."""
        assert component.state_get("missing") is None

    def test_delete_removes_key(self, component):
        """§4.4: state_delete removes the key; state_get returns None thereafter."""
        component.state_set("x", 1)
        component.state_delete("x")
        assert component.state_get("x") is None

    def test_observe_fires_on_set(self, component):
        """§4.4: callback registered via state_observe fires when the key is set."""
        received = []
        component.state_observe("watched", received.append)
        component.state_set("watched", 42)
        assert 42 in received

    def test_unobserve_stops_callbacks(self, component):
        """§4.4: state_unobserve stops the callback from firing."""
        received = []
        handle = component.state_observe("watched2", received.append)
        component.state_unobserve(handle)
        component.state_set("watched2", 99)
        assert 99 not in received


class TestPersistence:
    """§4.4 — JSON write-through persistence."""

    def test_state_persists_to_json(self, tmp_path):
        """§4.4: every state_set writes the full store to state.json via FilesystemComponent."""
        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        comp = AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )
        comp.state_set("persist_key", "persist_value")
        state_file = tmp_path / "state.json"
        assert state_file.exists()
        import json
        data = json.loads(state_file.read_text())
        assert data.get("persist_key") == "persist_value"

    def test_corrupt_state_starts_empty(self, tmp_path):
        """§4.4: corrupt state.json → empty store + WARNING logged; file renamed."""
        (tmp_path / "state.json").write_text("NOT JSON {{{}}")
        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        comp = AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )
        comp.load()
        assert comp.state_get("any_key") is None
        corrupt_files = list(tmp_path.glob("state.json.corrupt-*"))
        assert len(corrupt_files) == 1

    def test_missing_state_starts_empty(self, tmp_path):
        """§4.4: missing state.json → store starts empty, no error raised."""
        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        comp = AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )
        comp.load()
        assert comp.state_get("k") is None


class TestWriteWarningWindow:
    """S12 — 50 ms warning window parametrized."""

    @pytest.fixture()
    def component_with_log_capture(self, tmp_path):
        sig = SignalComponent()
        fs = FilesystemComponent()
        log = LoggingComponent(filesystem_component=fs, root=tmp_path)
        comp = AppStateComponent(
            signal_component=sig,
            filesystem_component=fs,
            logging_component=log,
            root=tmp_path,
        )
        return comp, log

    @pytest.mark.parametrize(
        "delay_ms, expect_warning",
        [
            (0, True),
            (10, True),
            (49, True),
            (51, False),
            (100, False),
        ],
    )
    def test_warning_emitted_within_window(
        self, component_with_log_capture, delay_ms, expect_warning
    ):
        """S12: WARNING is logged when two writes to the same key occur within 50 ms."""
        comp, log = component_with_log_capture
        comp.state_set("race_key", "first")
        time.sleep(delay_ms / 1000.0)
        comp.state_set("race_key", "second")
        warnings = log.captured_warnings()
        if expect_warning:
            assert any("race_key" in w for w in warnings)
        else:
            assert not any("race_key" in w for w in warnings)
