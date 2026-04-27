"""Tests for LoggingService — §5.6, §5.1, S8."""

import logging
from pathlib import Path

import pytest
from unittest.mock import MagicMock
from services.logging_service.service import LoggingServiceImpl


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: logging_service/manifest.json is valid under ServiceManifest schema."""
        import json
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/logging_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "logging_service"

    def test_manifest_no_depends_on(self):
        """§5.6: logging_service depends_on is empty."""
        import json
        data = json.loads(Path("services/logging_service/manifest.json").read_text())
        assert data.get("depends_on", []) == []


class TestLoggingServiceProtocol:
    """§5.6 — LoggingService protocol surface."""

    @pytest.fixture()
    def service(self, mock_logging_component):
        return LoggingServiceImpl(logging_component=mock_logging_component)

    def test_log_delegates_to_component(self, service, mock_logging_component):
        """§5.6: log delegates to LoggingComponent.log."""
        service.log("my_plugin", logging.INFO, "hello world")
        mock_logging_component.log.assert_called_once_with(
            "my_plugin", logging.INFO, "hello world"
        )

    def test_raise_alert_delegates_to_component(self, service, mock_logging_component):
        """§5.6: raise_alert delegates to LoggingComponent.raise_alert."""
        service.raise_alert("my_plugin", logging.ERROR, "something went wrong")
        mock_logging_component.raise_alert.assert_called_once_with(
            "my_plugin", logging.ERROR, "something went wrong"
        )

    @pytest.mark.parametrize(
        "level",
        [logging.WARNING, logging.ERROR, logging.CRITICAL],
    )
    def test_all_alert_levels_passed_through(self, service, mock_logging_component, level):
        """D9: logging_service passes WARNING, ERROR, CRITICAL levels to the component."""
        service.raise_alert("plugin", level, "msg")
        mock_logging_component.raise_alert.assert_called_with("plugin", level, "msg")

    def test_log_and_alert_are_independent_channels(self, service, mock_logging_component):
        """§5.6: log and raise_alert are independent — both can be called without interaction."""
        service.log("p", logging.WARNING, "warning log")
        service.raise_alert("p", logging.WARNING, "warning alert")
        assert mock_logging_component.log.call_count == 1
        assert mock_logging_component.raise_alert.call_count == 1
