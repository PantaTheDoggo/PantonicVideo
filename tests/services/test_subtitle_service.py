"""Tests for SubtitleService — §5.10, §5.1."""

import json
from pathlib import Path

import pytest
from unittest.mock import MagicMock
from services.subtitle_service.service import SubtitleServiceImpl
from contracts.subtitle import SrtOptions


class TestManifestValidation:
    """§5.1 — service manifest validates strictly."""

    def test_manifest_valid(self):
        """§5.1: subtitle_service/manifest.json is valid under ServiceManifest schema."""
        from infracore.manifest.service_manifest import ServiceManifest

        data = json.loads(Path("services/subtitle_service/manifest.json").read_text())
        manifest = ServiceManifest.model_validate(data)
        assert manifest.name == "subtitle_service"

    def test_manifest_depends_on_filesystem_service(self):
        """§5.10: subtitle_service depends_on filesystem_service >= 1.0."""
        data = json.loads(Path("services/subtitle_service/manifest.json").read_text())
        dep_names = [d["name"] for d in data.get("depends_on", [])]
        assert "filesystem_service" in dep_names


class TestSubtitleServiceProtocol:
    """§5.10 — SubtitleService protocol surface."""

    @pytest.fixture()
    def service(self, mock_filesystem_service):
        return SubtitleServiceImpl(filesystem_service=mock_filesystem_service)

    def test_text_to_srt_calls_filesystem_write(self, service, mock_filesystem_service, tmp_path):
        """§5.10: text_to_srt routes output through FilesystemService.write."""
        output = tmp_path / "output.srt"
        opts = SrtOptions()
        service.text_to_srt("Hello world.", output, opts)
        mock_filesystem_service.write.assert_called()

    def test_text_to_srt_uses_default_options(self, service, mock_filesystem_service, tmp_path):
        """§5.10: text_to_srt accepts default SrtOptions without error."""
        output = tmp_path / "default.srt"
        service.text_to_srt("Test text.", output, SrtOptions())
        mock_filesystem_service.write.assert_called()

    @pytest.mark.parametrize(
        "cps, max_line_chars",
        [
            (10, 30),
            (17, 42),
            (25, 60),
        ],
    )
    def test_text_to_srt_respects_pacing_options(
        self, service, mock_filesystem_service, tmp_path, cps, max_line_chars
    ):
        """§5.10: text_to_srt uses the SrtOptions pacing parameters."""
        output = tmp_path / f"out_{cps}.srt"
        opts = SrtOptions(cps=cps, max_line_chars=max_line_chars)
        service.text_to_srt("Some subtitle text here.", output, opts)
        mock_filesystem_service.write.assert_called()

    def test_text_to_srt_output_is_valid_srt_format(self, service, mock_filesystem_service, tmp_path):
        """§5.10 (integration): text_to_srt writes SRT-formatted content (index, timestamps, text)."""
        captured = {}

        def capture_write(path, data):
            captured["data"] = data

        mock_filesystem_service.write.side_effect = capture_write

        output = tmp_path / "check.srt"
        service.text_to_srt("Hello.", output, SrtOptions())
        assert "data" in captured
        content = captured["data"].decode("utf-8")
        assert "1" in content
        assert "-->" in content
        assert "Hello" in content


class TestSubtitleServiceIntegration:
    """§5.10 / §16.1 — integration smoke test (no real SRT library required for v1)."""

    def test_text_to_srt_produces_nonempty_file(self, tmp_path):
        """§5.10 (integration): text_to_srt produces a non-empty file on disk."""
        written = {}

        class RealFsService:
            def write(self, path, data):
                written[path] = data

            def read(self, path):
                return written.get(path, b"")

            def exists(self, path):
                return path in written

        svc = SubtitleServiceImpl(filesystem_service=RealFsService())
        output = tmp_path / "real.srt"
        svc.text_to_srt("A longer subtitle text to generate.", output, SrtOptions())
        assert output in written
        assert len(written[output]) > 0
