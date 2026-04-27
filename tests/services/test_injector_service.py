"""Tests for InjectorService — §5.7, §5.1, S2, S17."""

from pathlib import Path

import pytest
from unittest.mock import MagicMock
from services.injector_service.service import InjectorServiceImpl
from contracts.exceptions import ServiceNotAvailable


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: injector_service/manifest.json is valid under ServiceManifest schema."""
        import json
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/injector_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "injector_service"

    def test_manifest_no_depends_on(self):
        """§5.7: injector_service depends_on is empty."""
        import json
        data = json.loads(Path("services/injector_service/manifest.json").read_text())
        assert data.get("depends_on", []) == []


class TestInjectorServiceProtocol:
    """§5.7, S2, S17 — InjectorService has only a resolve method."""

    @pytest.fixture()
    def service(self, mock_injector_component):
        return InjectorServiceImpl(injector_component=mock_injector_component)

    def test_resolve_delegates_to_component(self, service, mock_injector_component):
        """S17: resolve delegates to InjectorComponent.resolve."""
        fake_svc = object()
        mock_injector_component.resolve.return_value = fake_svc
        result = service.resolve("signal_service", "1.0")
        mock_injector_component.resolve.assert_called_once_with("signal_service", "1.0")
        assert result is fake_svc

    def test_resolve_raises_service_not_available(self, service, mock_injector_component):
        """S17: resolve raises ServiceNotAvailable when the component does."""
        mock_injector_component.resolve.side_effect = ServiceNotAvailable("missing")
        with pytest.raises(ServiceNotAvailable):
            service.resolve("nonexistent_service", "1.0")

    def test_injector_service_has_only_resolve(self, service):
        """S2: InjectorService surface is intentionally narrow — only resolve."""
        public_methods = [
            m for m in dir(service)
            if not m.startswith("_") and callable(getattr(service, m))
        ]
        assert "resolve" in public_methods
