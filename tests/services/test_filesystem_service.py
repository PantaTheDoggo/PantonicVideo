"""Tests for FilesystemService — §5.4, §5.1."""

from pathlib import Path

import pytest
from unittest.mock import MagicMock
from services.filesystem_service.service import FilesystemServiceImpl


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: filesystem_service/manifest.json is valid under ServiceManifest schema."""
        import json
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/filesystem_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "filesystem_service"

    def test_manifest_depends_on_signal_service(self):
        """§5.4: filesystem_service depends_on signal_service >= 1.0."""
        import json
        data = json.loads(Path("services/filesystem_service/manifest.json").read_text())
        dep_names = [d["name"] for d in data.get("depends_on", [])]
        assert "signal_service" in dep_names


class TestFilesystemServiceProtocol:
    """§5.4 — FilesystemService protocol surface."""

    @pytest.fixture()
    def service(self, mock_filesystem_component, mock_signal_service):
        return FilesystemServiceImpl(
            filesystem_component=mock_filesystem_component,
            signal_service=mock_signal_service,
        )

    def test_read_delegates_to_component(self, service, mock_filesystem_component):
        """§5.4: read delegates to FilesystemComponent.read_file."""
        mock_filesystem_component.read_file.return_value = b"data"
        result = service.read(Path("/tmp/f"))
        assert result == b"data"
        mock_filesystem_component.read_file.assert_called_once_with(Path("/tmp/f"))

    def test_write_delegates_to_component(self, service, mock_filesystem_component):
        """§5.4: write delegates to FilesystemComponent.write_file (serialized per path)."""
        service.write(Path("/tmp/f"), b"hello")
        mock_filesystem_component.write_file.assert_called_once_with(Path("/tmp/f"), b"hello")

    def test_list_delegates_to_component(self, service, mock_filesystem_component):
        """§5.4: list delegates to FilesystemComponent.list_dir."""
        mock_filesystem_component.list_dir.return_value = []
        service.list(Path("/tmp"))
        mock_filesystem_component.list_dir.assert_called_once_with(Path("/tmp"))

    def test_exists_delegates_to_component(self, service, mock_filesystem_component):
        """§5.4: exists delegates to FilesystemComponent.exists."""
        mock_filesystem_component.exists.return_value = True
        assert service.exists(Path("/tmp/f")) is True

    def test_delete_delegates_to_component(self, service, mock_filesystem_component):
        """§5.4: delete delegates to FilesystemComponent.delete."""
        service.delete(Path("/tmp/f"))
        mock_filesystem_component.delete.assert_called_once_with(Path("/tmp/f"))

    def test_make_dir_delegates_to_component(self, service, mock_filesystem_component):
        """§5.4: make_dir delegates to FilesystemComponent.make_dir."""
        service.make_dir(Path("/tmp/d"))
        mock_filesystem_component.make_dir.assert_called()

    def test_watch_delegates_to_signal_service(self, service, mock_signal_service):
        """§5.4: watch delegates to SignalService.signal_for_path."""
        mock_signal_service.signal_for_path.return_value = MagicMock()
        service.watch(Path("/tmp"))
        mock_signal_service.signal_for_path.assert_called_once_with(Path("/tmp"))
