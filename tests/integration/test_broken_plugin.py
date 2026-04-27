"""Integration test — §16.2 scenario 2: broken-plugin tolerance."""

import json
from pathlib import Path

import pytest


@pytest.fixture()
def root_with_broken_plugin(pantonicvideo_root):
    """Add a third-party plugin with a malformed manifest to the user-data plugins folder."""
    broken_dir = pantonicvideo_root / "plugins" / "broken_plugin"
    broken_dir.mkdir()
    (broken_dir / "manifest.json").write_text("NOT VALID JSON {{}")
    return pantonicvideo_root


@pytest.fixture()
def root_with_exception_raising_plugin(pantonicvideo_root, tmp_path):
    """Add a third-party plugin whose on_load raises RuntimeError."""
    plugin_dir = pantonicvideo_root / "plugins" / "exploding_plugin"
    plugin_dir.mkdir()
    manifest = {
        "name": "exploding_plugin",
        "version": "1.0.0",
        "contracts_min_version": "1.0",
        "author": "Test",
        "description": "A plugin that explodes on load.",
        "entry_point": "plugin:ExplodingPlugin",
        "required_services": [],
        "inputs": [],
        "outputs": [],
        "permissions": [],
    }
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
    (plugin_dir / "plugin.py").write_text(
        "class ExplodingPlugin:\n"
        "    def on_load(self, services): raise RuntimeError('boom')\n"
        "    def on_enable(self): pass\n"
        "    def on_disable(self): pass\n"
        "    def on_unload(self): pass\n"
    )
    return pantonicvideo_root


def test_malformed_manifest_plugin_appears_as_failed(root_with_broken_plugin, app_runner):
    """§16.2 / §11: a plugin with a malformed manifest appears as 'failed' in the registry."""
    result = app_runner(root=root_with_broken_plugin)
    failed = [p for p in result.plugin_records if p.name == "broken_plugin"]
    assert len(failed) == 1
    assert failed[0].status == "failed"


def test_broken_plugin_does_not_abort_startup(root_with_broken_plugin, app_runner):
    """§16.2 / PRD §2.3: a broken plugin does not abort startup; the app is otherwise healthy."""
    result = app_runner(root=root_with_broken_plugin)
    assert result.startup_healthy is True


def test_broken_plugin_raises_alert(root_with_broken_plugin, app_runner):
    """§11: a broken plugin surfaces under the alert icon."""
    result = app_runner(root=root_with_broken_plugin)
    assert result.alert_count >= 1


def test_exception_in_on_load_marks_plugin_failed(root_with_exception_raising_plugin, app_runner):
    """§6.2 / §16.2: a plugin that raises in on_load is marked 'failed' with the exception as reason."""
    result = app_runner(root=root_with_exception_raising_plugin)
    failed = [p for p in result.plugin_records if p.name == "exploding_plugin"]
    assert len(failed) == 1
    assert failed[0].status == "failed"
    assert "boom" in failed[0].failure_reason or "RuntimeError" in failed[0].failure_reason


def test_missing_required_service_marks_plugin_failed(pantonicvideo_root, app_runner):
    """§9.7 / §16.2: a plugin whose required_services cannot be satisfied is marked 'failed'."""
    plugin_dir = pantonicvideo_root / "plugins" / "needy_plugin"
    plugin_dir.mkdir()
    manifest = {
        "name": "needy_plugin",
        "version": "1.0.0",
        "contracts_min_version": "1.0",
        "author": "Test",
        "description": "Needs a service that doesn't exist.",
        "entry_point": "plugin:NeedyPlugin",
        "required_services": [{"name": "nonexistent_service", "min_version": "1.0"}],
        "inputs": [],
        "outputs": [],
        "permissions": [],
    }
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
    result = app_runner()
    failed = [p for p in result.plugin_records if p.name == "needy_plugin"]
    assert len(failed) == 1
    assert failed[0].status == "failed"
