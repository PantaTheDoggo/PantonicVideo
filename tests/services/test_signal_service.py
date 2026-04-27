"""Tests for SignalService — §5.2, §5.1."""

import pytest
from unittest.mock import MagicMock
from services.signal_service.service import SignalServiceImpl
from contracts.signals import Signal, Subscription


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: signal_service/manifest.json is valid under ServiceManifest schema."""
        import json
        from pathlib import Path
        from infracore.manifest.service_manifest import ServiceManifest

        manifest_path = Path("services/signal_service/manifest.json")
        data = json.loads(manifest_path.read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "signal_service"

    def test_manifest_service_api_version_present(self):
        """§5.1: manifest declares service_api_version."""
        import json
        from pathlib import Path
        data = json.loads(Path("services/signal_service/manifest.json").read_text())
        assert "service_api_version" in data

    def test_manifest_no_depends_on(self):
        """§5.2: signal_service depends_on is empty (wraps component directly)."""
        import json
        from pathlib import Path
        data = json.loads(Path("services/signal_service/manifest.json").read_text())
        assert data.get("depends_on", []) == []


class TestSignalServiceProtocol:
    """§5.2 — SignalService protocol surface."""

    @pytest.fixture()
    def service(self, mock_signal_component):
        return SignalServiceImpl(signal_component=mock_signal_component)

    def test_signal_for_state_returns_signal(self, service, mock_signal_component):
        """§5.2: signal_for_state returns a Signal object."""
        mock_signal_component.make_signal.return_value = MagicMock()
        result = service.signal_for_state("some_key")
        assert result is not None

    def test_signal_for_path_returns_signal(self, service, mock_signal_component):
        """§5.2: signal_for_path returns a Signal object."""
        from pathlib import Path
        result = service.signal_for_path(Path("/tmp"))
        assert result is not None

    def test_signal_for_plugins_returns_signal(self, service):
        """§5.2: signal_for_plugins returns a Signal object."""
        result = service.signal_for_plugins()
        assert result is not None

    def test_signal_for_alerts_returns_signal(self, service):
        """§5.2: signal_for_alerts returns a Signal object."""
        result = service.signal_for_alerts()
        assert result is not None

    def test_subscribe_delegates_to_component(self, service, mock_signal_component):
        """§5.2: subscribe delegates to SignalComponent.subscribe."""
        sig = MagicMock()
        cb = lambda x: None
        service.subscribe(sig, cb)
        mock_signal_component.subscribe.assert_called_once_with(sig, cb)

    def test_unsubscribe_delegates_to_component(self, service, mock_signal_component):
        """§5.2: unsubscribe delegates to SignalComponent.unsubscribe."""
        sub = MagicMock()
        service.unsubscribe(sub)
        mock_signal_component.unsubscribe.assert_called_once_with(sub)
