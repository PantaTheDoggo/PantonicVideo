"""Tests for AppStateService — §5.3, §5.1, S10."""

import pytest
from unittest.mock import MagicMock
from services.app_state_service.service import AppStateServiceImpl


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: app_state_service/manifest.json is valid under ServiceManifest schema."""
        import json
        from pathlib import Path
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/app_state_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "app_state_service"

    def test_manifest_depends_on_signal_service(self):
        """§5.3: app_state_service depends_on signal_service >= 1.0."""
        import json
        from pathlib import Path
        data = json.loads(Path("services/app_state_service/manifest.json").read_text())
        dep_names = [d["name"] for d in data.get("depends_on", [])]
        assert "signal_service" in dep_names


class TestAppStateServiceProtocol:
    """§5.3 — AppStateService protocol surface."""

    @pytest.fixture()
    def service(self, mock_app_state_component, mock_signal_service):
        return AppStateServiceImpl(
            app_state_component=mock_app_state_component,
            signal_service=mock_signal_service,
        )

    def test_get_delegates_to_component(self, service, mock_app_state_component):
        """§5.3: get delegates to AppStateComponent.state_get."""
        mock_app_state_component.state_get.return_value = "val"
        assert service.get("k") == "val"
        mock_app_state_component.state_get.assert_called_once_with("k")

    def test_set_delegates_to_component(self, service, mock_app_state_component):
        """§5.3: set delegates to AppStateComponent.state_set."""
        service.set("k", "v")
        mock_app_state_component.state_set.assert_called_once_with("k", "v")

    def test_delete_delegates_to_component(self, service, mock_app_state_component):
        """§5.3: delete delegates to AppStateComponent.state_delete."""
        service.delete("k")
        mock_app_state_component.state_delete.assert_called_once_with("k")

    def test_observe_returns_signal(self, service, mock_signal_service):
        """§5.3: observe delegates to SignalService.signal_for_state."""
        service.observe("some_key")
        mock_signal_service.signal_for_state.assert_called_once_with("some_key")


class TestPluginEnabledKeyConvention:
    """S10 — plugins.<name>.enabled key convention."""

    @pytest.fixture()
    def service(self, mock_app_state_component, mock_signal_service):
        return AppStateServiceImpl(
            app_state_component=mock_app_state_component,
            signal_service=mock_signal_service,
        )

    @pytest.mark.parametrize(
        "plugin_name",
        ["project_launcher", "image_cropping", "subtitle_text_tool"],
    )
    def test_plugin_enabled_key_format(self, service, mock_app_state_component, plugin_name):
        """S10: plugin enabled state is stored under 'plugins.<name>.enabled'."""
        key = f"plugins.{plugin_name}.enabled"
        service.set(key, True)
        mock_app_state_component.state_set.assert_called_with(key, True)
