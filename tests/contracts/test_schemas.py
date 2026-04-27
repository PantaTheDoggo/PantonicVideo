"""Tests for contracts Pydantic schemas — §3, §3.2."""

import pytest
from pydantic import ValidationError


class TestSignalsContracts:
    """§3.2 — contracts.signals schema."""

    def test_subscription_handle_is_newtype_of_uuid(self):
        """§3.2: SubscriptionHandle is a NewType over uuid.UUID."""
        import uuid
        from contracts.signals import SubscriptionHandle
        h = SubscriptionHandle(uuid.uuid4())
        assert isinstance(h, uuid.UUID)

    def test_signal_protocol_exists(self):
        """§3.2: contracts.signals exposes Signal[T] Protocol."""
        from contracts.signals import Signal
        assert Signal is not None

    def test_subscription_protocol_exists(self):
        """§3.2: contracts.signals exposes Subscription Protocol."""
        from contracts.signals import Subscription
        assert Subscription is not None


class TestFilesystemContracts:
    """§3.2 — contracts.filesystem schema."""

    def test_filesystem_event_valid(self):
        """§3.2: FilesystemEvent accepts valid path/kind/timestamp."""
        from contracts.filesystem import FilesystemEvent
        from datetime import datetime, timezone
        from pathlib import Path
        evt = FilesystemEvent(
            path=Path("/tmp/x.txt"),
            kind="created",
            timestamp=datetime.now(timezone.utc),
        )
        assert evt.kind == "created"

    @pytest.mark.parametrize(
        "kind",
        ["created", "modified", "deleted"],
    )
    def test_filesystem_event_kinds(self, kind):
        """§3.2: FilesystemEvent kind accepts created, modified, deleted."""
        from contracts.filesystem import FilesystemEvent
        from datetime import datetime, timezone
        from pathlib import Path
        evt = FilesystemEvent(
            path=Path("/tmp/f"),
            kind=kind,
            timestamp=datetime.now(timezone.utc),
        )
        assert evt.kind == kind

    def test_filesystem_event_rejects_invalid_kind(self):
        """§3.2: FilesystemEvent rejects unknown kind values."""
        from contracts.filesystem import FilesystemEvent
        from datetime import datetime, timezone
        from pathlib import Path
        with pytest.raises(ValidationError):
            FilesystemEvent(
                path=Path("/tmp/f"),
                kind="exploded",
                timestamp=datetime.now(timezone.utc),
            )

    def test_filesystem_service_protocol_exists(self):
        """§3.2: contracts.filesystem exposes FilesystemService Protocol."""
        from contracts.filesystem import FilesystemService
        assert FilesystemService is not None


class TestStateContracts:
    """§3.2 — contracts.state schema."""

    def test_app_state_service_protocol_exists(self):
        """§3.2: contracts.state exposes AppStateService Protocol."""
        from contracts.state import AppStateService
        assert AppStateService is not None


class TestPluginRegistryContracts:
    """§3.2 — contracts.plugin_registry schema."""

    def test_plugin_record_valid(self):
        """§3.2: PluginRecord Pydantic model accepts valid data."""
        from contracts.plugin_registry import PluginRecord, PluginStatus
        record = PluginRecord(
            name="test",
            version="1.0.0",
            description="desc",
            author="auth",
            status=PluginStatus.loaded,
            failure_reason=None,
            is_builtin=True,
        )
        assert record.name == "test"

    def test_plugin_record_rejects_missing_name(self):
        """§3.2: PluginRecord rejects records with missing required 'name' field."""
        from contracts.plugin_registry import PluginRecord, PluginStatus
        with pytest.raises(ValidationError):
            PluginRecord(
                version="1.0.0",
                description="d",
                author="a",
                status=PluginStatus.loaded,
                failure_reason=None,
                is_builtin=False,
            )

    @pytest.mark.parametrize(
        "status_str",
        ["loaded", "enabled", "disabled", "failed"],
    )
    def test_plugin_status_enum_values(self, status_str):
        """§3.2: PluginStatus enum has loaded, enabled, disabled, failed values."""
        from contracts.plugin_registry import PluginStatus
        status = PluginStatus(status_str)
        assert status.value == status_str


class TestLoggingContracts:
    """§3.2 — contracts.logging schema."""

    def test_alert_entry_valid(self):
        """§3.2: AlertEntry Pydantic model accepts valid data."""
        from contracts.logging import AlertEntry
        from datetime import datetime, timezone
        entry = AlertEntry(
            plugin="some_plugin",
            level=30,
            summary="Warning message",
            timestamp=datetime.now(timezone.utc),
        )
        assert entry.acknowledged is False

    def test_alert_entry_rejects_missing_plugin(self):
        """§3.2: AlertEntry rejects records with missing 'plugin' field."""
        from contracts.logging import AlertEntry
        from datetime import datetime, timezone
        with pytest.raises(ValidationError):
            AlertEntry(level=30, summary="msg", timestamp=datetime.now(timezone.utc))

    def test_log_level_enum_aliased_to_stdlib(self):
        """§3.2: LogLevel enum values match stdlib logging levels."""
        import logging as stdlib_logging
        from contracts.logging import LogLevel
        assert LogLevel.WARNING == stdlib_logging.WARNING
        assert LogLevel.ERROR == stdlib_logging.ERROR
        assert LogLevel.CRITICAL == stdlib_logging.CRITICAL

    def test_logging_service_protocol_exists(self):
        """§3.2: contracts.logging exposes LoggingService Protocol."""
        from contracts.logging import LoggingService
        assert LoggingService is not None


class TestInjectorContracts:
    """§3.2, S2, S17 — contracts.injector schema."""

    def test_injector_service_protocol_exists(self):
        """S17: contracts.injector exposes InjectorService Protocol with resolve method."""
        from contracts.injector import InjectorService
        import inspect
        assert hasattr(InjectorService, "resolve") or "resolve" in str(InjectorService)


class TestProjectContracts:
    """§3.2 — contracts.project schema."""

    def test_project_model_valid(self):
        """§3.2: Project Pydantic model accepts a valid central_folder path."""
        from contracts.project import Project
        from pathlib import Path
        p = Project(central_folder=Path("/projects/myproject"))
        assert p.central_folder == Path("/projects/myproject")

    def test_project_metadata_defaults(self):
        """§3.2: ProjectMetadata has default-empty list fields."""
        from contracts.project import ProjectMetadata
        meta = ProjectMetadata()
        assert meta.image_source_folders == []
        assert meta.audio_source_folders == []


class TestImageContracts:
    """§3.2 — contracts.image schema."""

    def test_crop_rect_valid(self):
        """§3.2: CropRect accepts valid left/top/width/height integer fields."""
        from contracts.image import CropRect
        rect = CropRect(left=0, top=0, width=100, height=100)
        assert rect.width == 100

    def test_dimensions_valid(self):
        """§3.2: Dimensions accepts valid width/height integer fields."""
        from contracts.image import Dimensions
        dims = Dimensions(width=1920, height=1080)
        assert dims.height == 1080

    @pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
    def test_image_format_enum_values(self, fmt):
        """§3.2: ImageFormat enum has PNG and JPEG values for v1."""
        from contracts.image import ImageFormat
        assert ImageFormat(fmt).value == fmt


class TestSubtitleContracts:
    """§3.2 — contracts.subtitle schema."""

    def test_srt_options_defaults(self):
        """§3.2: SrtOptions has default cps=17, max_line_chars=42, min_duration_ms=1000, gap_ms=100."""
        from contracts.subtitle import SrtOptions
        opts = SrtOptions()
        assert opts.cps == 17
        assert opts.max_line_chars == 42
        assert opts.min_duration_ms == 1000
        assert opts.gap_ms == 100


class TestManifestContracts:
    """§3.2, §6.1 — contracts.manifest plugin-facing model."""

    def test_required_service_valid(self):
        """§3.2: RequiredService Pydantic model accepts name and min_version."""
        from contracts.manifest import RequiredService
        rs = RequiredService(name="image_service", min_version="1.0")
        assert rs.name == "image_service"

    def test_required_service_rejects_missing_name(self):
        """§3.2: RequiredService rejects records missing 'name'."""
        from contracts.manifest import RequiredService
        with pytest.raises(ValidationError):
            RequiredService(min_version="1.0")

    def test_plugin_manifest_contract_valid(self):
        """§6.1: plugin-facing manifest model accepts a valid full manifest."""
        from contracts.manifest import PluginManifest, RequiredService
        manifest = PluginManifest(
            name="image_cropping",
            version="1.0.0",
            contracts_min_version="1.0",
            author="PantonicVideo",
            description="Crop and resize static images.",
            entry_point="plugin:ImageCroppingPlugin",
            required_services=[
                RequiredService(name="image_service", min_version="1.0"),
            ],
            inputs=[],
            outputs=[],
            permissions=[],
        )
        assert manifest.name == "image_cropping"

    def test_plugin_manifest_rejects_extra_fields(self):
        """§6.1: plugin-facing manifest model rejects unknown fields (strict mode)."""
        from contracts.manifest import PluginManifest
        with pytest.raises((ValidationError, TypeError)):
            PluginManifest(
                name="bad",
                version="1.0.0",
                contracts_min_version="1.0",
                author="a",
                description="d",
                entry_point="p:C",
                required_services=[],
                inputs=[],
                outputs=[],
                permissions=[],
                unknown_field="should fail",
            )
