"""Shared fixtures for services tests — §16.1 (Pillow/SRT stubs, mocked components)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stub: Pillow (PIL.Image)
# ---------------------------------------------------------------------------

class _FakePilImage:
    """Minimal stub for PIL.Image.Image used in image_service unit tests."""

    def __init__(self, size=(100, 100)):
        self.size = size

    def crop(self, box):
        return _FakePilImage(size=(box[2] - box[0], box[3] - box[1]))

    def resize(self, size, resample=None):
        return _FakePilImage(size=size)

    def save(self, fp, format=None, **kwargs):
        fp = Path(fp) if not isinstance(fp, Path) else fp
        fp.write_bytes(b"FAKE_IMAGE_DATA")


class _FakePIL:
    class Image:
        LANCZOS = 1

        @staticmethod
        def open(path):
            return _FakePilImage()


@pytest.fixture()
def stub_pillow():
    """Replace PIL.Image with a minimal stub so image_service tests don't need Pillow installed."""
    with patch.dict("sys.modules", {"PIL": _FakePIL, "PIL.Image": _FakePIL.Image}):
        yield _FakePIL


# ---------------------------------------------------------------------------
# Stub: SRT library (if any third-party SRT lib is used)
# ---------------------------------------------------------------------------

class _FakeSrtLib:
    """Minimal stub for any SRT parsing/writing library used in subtitle_service."""

    @staticmethod
    def compose(entries):
        lines = []
        for i, (start_ms, end_ms, text) in enumerate(entries, start=1):
            lines.append(f"{i}")
            lines.append(f"00:00:{start_ms // 1000:02d},000 --> 00:00:{end_ms // 1000:02d},000")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)


@pytest.fixture()
def stub_srt():
    """Provide a minimal SRT stub for subtitle_service unit tests."""
    return _FakeSrtLib


# ---------------------------------------------------------------------------
# Mocked components (for expression services — §16.1)
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_signal_component():
    """Mocked SignalComponent for expression-service tests (§16.1)."""
    comp = MagicMock()
    import uuid as _uuid
    comp.make_signal.return_value = MagicMock(current_value=None)
    comp.subscribe.return_value = MagicMock()
    return comp


@pytest.fixture()
def mock_filesystem_component():
    """Mocked FilesystemComponent for expression-service tests (§16.1)."""
    comp = MagicMock()
    comp.read_file.return_value = b""
    comp.exists.return_value = False
    return comp


@pytest.fixture()
def mock_app_state_component():
    """Mocked AppStateComponent for expression-service tests (§16.1)."""
    comp = MagicMock()
    comp.state_get.return_value = None
    return comp


@pytest.fixture()
def mock_plugin_registry_component():
    """Mocked PluginRegistryComponent for expression-service tests (§16.1)."""
    comp = MagicMock()
    comp.list_plugins.return_value = []
    return comp


@pytest.fixture()
def mock_logging_component():
    """Mocked LoggingComponent for expression-service tests (§16.1)."""
    return MagicMock()


@pytest.fixture()
def mock_injector_component():
    """Mocked InjectorComponent for expression-service tests (§16.1)."""
    comp = MagicMock()
    return comp


# ---------------------------------------------------------------------------
# Mocked services (for domain-service tests — §16.1)
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_signal_service():
    """Mocked SignalService for domain-service tests (§16.1)."""
    svc = MagicMock()
    svc.subscribe.return_value = MagicMock()
    return svc


@pytest.fixture()
def mock_filesystem_service(tmp_path):
    """Mocked FilesystemService backed by tmp_path writes for domain-service tests."""
    svc = MagicMock()
    _store: dict[Path, bytes] = {}

    def _write(path, data):
        _store[Path(path)] = data
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(data)

    def _read(path):
        return Path(path).read_bytes()

    def _exists(path):
        return Path(path).exists()

    svc.write.side_effect = _write
    svc.read.side_effect = _read
    svc.exists.side_effect = _exists
    return svc


@pytest.fixture()
def mock_app_state_service():
    """Mocked AppStateService for domain-service tests (§16.1)."""
    svc = MagicMock()
    _kv: dict[str, Any] = {}

    def _get(key):
        return _kv.get(key)

    def _set(key, value):
        _kv[key] = value

    svc.get.side_effect = _get
    svc.set.side_effect = _set
    return svc


@pytest.fixture()
def mock_logging_service():
    """Mocked LoggingService for domain-service tests (§16.1)."""
    return MagicMock()
