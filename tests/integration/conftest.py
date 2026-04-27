"""Shared fixtures for integration tests — §16.2, reusable temp <pantonicvideo-root>."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def pantonicvideo_root(tmp_path):
    """Create a minimal temporary <pantonicvideo-root> directory structure."""
    root = tmp_path / "pantonicvideo_root"
    root.mkdir()
    (root / "logs").mkdir()
    (root / "logs" / "plugins").mkdir()
    (root / "plugins").mkdir()
    return root


@pytest.fixture()
def app_runner(pantonicvideo_root, monkeypatch):
    """Run infracore/app.py against the temporary root; returns the exit status."""
    import importlib
    import infracore.app as app_module

    def run(**kwargs):
        root = kwargs.pop("root", pantonicvideo_root)
        return app_module.run(root=root, headless=True, **kwargs)

    return run
