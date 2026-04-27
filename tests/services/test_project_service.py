"""Tests for ProjectService — §5.8, §5.1, S13."""

import json
from pathlib import Path

import pytest
from unittest.mock import MagicMock
from services.project_service.service import ProjectServiceImpl
from contracts.project import Project, ProjectMetadata


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: project_service/manifest.json is valid under ServiceManifest schema."""
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/project_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "project_service"

    def test_manifest_depends_on_required_services(self):
        """§5.8: project_service depends_on app_state_service, filesystem_service, signal_service."""
        data = json.loads(Path("services/project_service/manifest.json").read_text())
        dep_names = [d["name"] for d in data.get("depends_on", [])]
        assert "app_state_service" in dep_names
        assert "filesystem_service" in dep_names
        assert "signal_service" in dep_names


class TestProjectServiceProtocol:
    """§5.8 — ProjectService protocol surface."""

    @pytest.fixture()
    def service(self, mock_app_state_service, mock_filesystem_service, mock_signal_service):
        return ProjectServiceImpl(
            app_state_service=mock_app_state_service,
            filesystem_service=mock_filesystem_service,
            signal_service=mock_signal_service,
        )

    def test_get_current_returns_none_when_unset(self, service, mock_app_state_service):
        """§5.8: get_current returns None when project.path is not set."""
        mock_app_state_service.get.return_value = None
        result = service.get_current()
        assert result is None

    def test_set_current_creates_metadata_when_missing(self, service, mock_filesystem_service, tmp_path):
        """§5.8: set_current creates pantonicvideo-project.json when absent."""
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()
        mock_filesystem_service.exists.return_value = False
        service.set_current(project_dir)
        mock_filesystem_service.write.assert_called()

    def test_set_current_writes_project_path_to_state(self, service, mock_app_state_service, tmp_path):
        """§5.8: set_current writes project.path to AppStateService."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        mock_filesystem_service = service._filesystem_service if hasattr(service, "_filesystem_service") else MagicMock()
        service.set_current(project_dir)
        mock_app_state_service.set.assert_called_with("project.path", str(project_dir))

    def test_get_metadata_returns_project_metadata(self, service, mock_filesystem_service, tmp_path):
        """§5.8: get_metadata returns a ProjectMetadata instance."""
        meta = ProjectMetadata()
        mock_filesystem_service.read.return_value = meta.model_dump_json().encode()
        mock_filesystem_service.exists.return_value = True
        result = service.get_metadata()
        assert isinstance(result, ProjectMetadata)

    def test_update_metadata_uses_filesystem_service(self, service, mock_filesystem_service, mock_app_state_service, tmp_path):
        """S13: update_metadata routes through FilesystemService (per-path serialization)."""
        project_dir = tmp_path / "proj2"
        project_dir.mkdir()
        mock_app_state_service.get.return_value = str(project_dir)
        mock_filesystem_service.exists.return_value = True
        meta = ProjectMetadata()
        mock_filesystem_service.read.return_value = meta.model_dump_json().encode()

        def updater(m):
            m.image_source_folders = [Path("/images")]
            return m

        service.update_metadata(updater)
        mock_filesystem_service.write.assert_called()

    def test_observe_current_delegates_to_signal_service(self, service, mock_signal_service):
        """§5.8: observe_current delegates to SignalService.signal_for_state('project.path')."""
        service.observe_current()
        mock_signal_service.signal_for_state.assert_called_with("project.path")


class TestProjectServiceIntegration:
    """§5.8 / §16.1 — one integration smoke test with real filesystem writes."""

    def test_set_current_and_get_current_roundtrip(self, tmp_path):
        """§5.8 (integration): set_current then get_current returns the same project."""
        from infracore.bootstrap_components.signal_component.signal import SignalComponent
        from infracore.bootstrap_components.filesystem_component.filesystem import FilesystemComponent
        from infracore.bootstrap_components.app_state_component.app_state import AppStateComponent
        from infracore.bootstrap_components.logging_component.logging import LoggingComponent
        from services.signal_service.service import SignalServiceImpl
        from services.filesystem_service.service import FilesystemServiceImpl
        from services.app_state_service.service import AppStateServiceImpl

        sig_comp = SignalComponent()
        fs_comp = FilesystemComponent()
        log_comp = LoggingComponent(filesystem_component=fs_comp, root=tmp_path)
        state_comp = AppStateComponent(
            signal_component=sig_comp,
            filesystem_component=fs_comp,
            logging_component=log_comp,
            root=tmp_path,
        )
        sig_svc = SignalServiceImpl(signal_component=sig_comp)
        fs_svc = FilesystemServiceImpl(filesystem_component=fs_comp, signal_service=sig_svc)
        state_svc = AppStateServiceImpl(
            app_state_component=state_comp,
            signal_service=sig_svc,
        )
        svc = ProjectServiceImpl(
            app_state_service=state_svc,
            filesystem_service=fs_svc,
            signal_service=sig_svc,
        )
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()
        svc.set_current(project_dir)
        project = svc.get_current()
        assert project is not None
        assert project.central_folder == project_dir
