"""Integration test — §16.2 scenario 3: pre-seeded state.json enabling Image Cropping."""

import json

import pytest


@pytest.fixture()
def root_with_image_cropping_enabled(pantonicvideo_root):
    """Write a state.json that enables image_cropping."""
    state = {
        "plugins.image_cropping.enabled": True,
        "plugins.project_launcher.enabled": True,
    }
    (pantonicvideo_root / "state.json").write_text(json.dumps(state))
    return pantonicvideo_root


def test_image_cropping_enabled_from_state(root_with_image_cropping_enabled, app_runner):
    """§16.2 / §9.11: when state.json has plugins.image_cropping.enabled=True, image_cropping is enabled at launch."""
    result = app_runner(root=root_with_image_cropping_enabled)
    plugin = next((p for p in result.plugin_records if p.name == "image_cropping"), None)
    assert plugin is not None
    assert plugin.status == "enabled"


def test_project_launcher_also_enabled(root_with_image_cropping_enabled, app_runner):
    """§16.2 / §9.11: project_launcher is also enabled when its persisted state says so."""
    result = app_runner(root=root_with_image_cropping_enabled)
    plugin = next((p for p in result.plugin_records if p.name == "project_launcher"), None)
    assert plugin is not None
    assert plugin.status == "enabled"


def test_subtitle_tool_not_enabled(root_with_image_cropping_enabled, app_runner):
    """§16.2 / §9.11: subtitle_text_tool remains loaded (not enabled) when state does not enable it."""
    result = app_runner(root=root_with_image_cropping_enabled)
    plugin = next((p for p in result.plugin_records if p.name == "subtitle_text_tool"), None)
    assert plugin is not None
    assert plugin.status == "loaded"
