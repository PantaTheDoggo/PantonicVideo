"""Tests for PluginRegistryComponent — §4.5, §9.3 (S6)."""

import pytest
from infracore.bootstrap_components.plugin_registry_component.plugin_registry import (
    PluginRegistryComponent,
    PluginRecord,
    PluginStatus,
)
from infracore.bootstrap_components.signal_component.signal import SignalComponent
from infracore.bootstrap_components.filesystem_component.filesystem import (
    FilesystemComponent,
)
from infracore.bootstrap_components.app_state_component.app_state import (
    AppStateComponent,
)
from infracore.bootstrap_components.logging_component.logging import LoggingComponent


@pytest.fixture()
def components(tmp_path):
    sig = SignalComponent()
    fs = FilesystemComponent()
    log = LoggingComponent(filesystem_component=fs, root=tmp_path)
    state = AppStateComponent(
        signal_component=sig,
        filesystem_component=fs,
        logging_component=log,
        root=tmp_path,
    )
    registry = PluginRegistryComponent(
        signal_component=sig,
        filesystem_component=fs,
        app_state_component=state,
        logging_component=log,
    )
    return registry


class TestComponentVersion:
    """§4.1 — __component_version__ declared."""

    def test_component_version_declared(self):
        """§4.1: PluginRegistryComponent module declares __component_version__ as semver."""
        import infracore.bootstrap_components.plugin_registry_component.plugin_registry as mod
        assert hasattr(mod, "__component_version__")
        v = mod.__component_version__
        parts = v.split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts)


class TestPluginRecord:
    """§4.5 — PluginRecord is a Pydantic v2 model with required fields."""

    def test_plugin_record_fields(self):
        """§4.5: PluginRecord has name, version, description, author, status, failure_reason, is_builtin."""
        record = PluginRecord(
            name="test_plugin",
            version="1.0.0",
            description="A test plugin.",
            author="PantonicVideo",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=True,
        )
        assert record.name == "test_plugin"
        assert record.is_builtin is True
        assert record.failure_reason is None

    @pytest.mark.parametrize(
        "status",
        [
            PluginStatus.loaded,
            PluginStatus.enabled,
            PluginStatus.disabled,
            PluginStatus.failed,
        ],
    )
    def test_plugin_status_values(self, status):
        """§4.5: PluginStatus enum has loaded, enabled, disabled, failed values."""
        record = PluginRecord(
            name="p",
            version="1.0.0",
            description="d",
            author="a",
            status=status,
            failure_reason=None,
            is_builtin=False,
        )
        assert record.status == status


class TestRecordOperations:
    """§4.5 — internal record_loaded, _record_failed, _set_enabled."""

    def test_record_loaded_adds_to_list(self, components):
        """§4.5: _record_loaded adds a PluginRecord with status=loaded."""
        record = PluginRecord(
            name="my_plugin",
            version="1.0.0",
            description="d",
            author="a",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=True,
        )
        components._record_loaded(record)
        plugins = components.list_plugins()
        names = [p.name for p in plugins]
        assert "my_plugin" in names

    def test_record_failed_sets_status(self, components):
        """§4.5: _record_failed records the plugin with status=failed and failure_reason."""
        components._record_failed("bad_plugin", "manifest invalid")
        plugins = components.list_plugins()
        bad = next((p for p in plugins if p.name == "bad_plugin"), None)
        assert bad is not None
        assert bad.status == PluginStatus.failed
        assert bad.failure_reason == "manifest invalid"

    def test_set_enabled_transitions_status(self, components):
        """§4.5: _set_enabled(True) transitions status from loaded to enabled."""
        record = PluginRecord(
            name="en_plugin",
            version="1.0.0",
            description="d",
            author="a",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=False,
        )
        components._record_loaded(record)
        components._set_enabled("en_plugin", True)
        plugins = components.list_plugins()
        en = next(p for p in plugins if p.name == "en_plugin")
        assert en.status == PluginStatus.enabled

    def test_observe_and_unobserve(self, components):
        """§4.5: observe_plugins fires callback when the plugin list changes."""
        received = []
        handle = components.observe_plugins(received.append)
        record = PluginRecord(
            name="observed_plugin",
            version="1.0.0",
            description="d",
            author="a",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=True,
        )
        components._record_loaded(record)
        assert len(received) > 0
        components.unobserve_plugins(handle)
        before = len(received)
        components._record_failed("another", "reason")
        assert len(received) == before


class TestBuiltinCollisionPolicy:
    """S6 — built-in wins; third-party with same name becomes failed."""

    def test_builtin_wins_on_name_collision(self, components):
        """S6: when a third-party plugin has the same name as a built-in, third-party is failed."""
        builtin = PluginRecord(
            name="project_launcher",
            version="1.0.0",
            description="d",
            author="PantonicVideo",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=True,
        )
        components._record_loaded(builtin)
        components._record_failed(
            "project_launcher", "name collides with built-in plugin `project_launcher`"
        )
        plugins = components.list_plugins()
        records = [p for p in plugins if p.name == "project_launcher"]
        builtin_record = next((r for r in records if r.is_builtin), None)
        assert builtin_record is not None
        assert builtin_record.status == PluginStatus.loaded
