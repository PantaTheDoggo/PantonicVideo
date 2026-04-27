"""Tests for PluginRegistryService — §5.5, §5.1, S10."""

from pathlib import Path

import pytest
from unittest.mock import MagicMock, call
from services.plugin_registry_service.service import PluginRegistryServiceImpl
from contracts.plugin_registry import PluginRecord, PluginStatus


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: plugin_registry_service/manifest.json is valid under ServiceManifest schema."""
        import json
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/plugin_registry_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "plugin_registry_service"

    def test_manifest_depends_on_signal_and_app_state(self):
        """§5.5: plugin_registry_service depends_on signal_service and app_state_service."""
        import json
        data = json.loads(Path("services/plugin_registry_service/manifest.json").read_text())
        dep_names = [d["name"] for d in data.get("depends_on", [])]
        assert "signal_service" in dep_names
        assert "app_state_service" in dep_names


class TestPluginRegistryServiceProtocol:
    """§5.5 — PluginRegistryService protocol surface."""

    @pytest.fixture()
    def service(
        self,
        mock_plugin_registry_component,
        mock_signal_service,
        mock_app_state_service,
    ):
        return PluginRegistryServiceImpl(
            plugin_registry_component=mock_plugin_registry_component,
            signal_service=mock_signal_service,
            app_state_service=mock_app_state_service,
        )

    @pytest.fixture()
    def loaded_record(self):
        return PluginRecord(
            name="test_plugin",
            version="1.0.0",
            description="d",
            author="a",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=False,
        )

    def test_list_plugins_delegates_to_component(self, service, mock_plugin_registry_component):
        """§5.5: list_plugins delegates to PluginRegistryComponent.list_plugins."""
        mock_plugin_registry_component.list_plugins.return_value = []
        result = service.list_plugins()
        assert result == []
        mock_plugin_registry_component.list_plugins.assert_called_once()

    def test_enable_sets_state_and_calls_lifecycle(self, service, mock_app_state_service, mock_plugin_registry_component):
        """S10: enable calls AppStateService.set('plugins.<name>.enabled', True) then calls lifecycle on_enable."""
        service.enable("test_plugin")
        mock_app_state_service.set.assert_called_with("plugins.test_plugin.enabled", True)

    def test_disable_sets_state_false(self, service, mock_app_state_service):
        """S10: disable calls AppStateService.set('plugins.<name>.enabled', False)."""
        service.disable("test_plugin")
        mock_app_state_service.set.assert_called_with("plugins.test_plugin.enabled", False)

    def test_observe_plugins_delegates_to_signal_service(self, service, mock_signal_service):
        """§5.5: observe_plugins delegates to SignalService.signal_for_plugins."""
        service.observe_plugins()
        mock_signal_service.signal_for_plugins.assert_called_once()
