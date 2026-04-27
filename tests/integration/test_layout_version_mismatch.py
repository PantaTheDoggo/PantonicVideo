"""Integration test — §16.2 scenario 4: unrecognized layout.json version falls back to first-run."""

import json

import pytest


@pytest.fixture()
def root_with_unknown_layout_version(pantonicvideo_root):
    """Write a layout.json with an unrecognized version number."""
    layout = {
        "version": 9999,
        "saved_at": "2026-01-01T00:00:00Z",
        "qt_state": "",
    }
    (pantonicvideo_root / "layout.json").write_text(json.dumps(layout))
    return pantonicvideo_root


@pytest.fixture()
def root_with_malformed_layout(pantonicvideo_root):
    """Write a layout.json that is invalid JSON."""
    (pantonicvideo_root / "layout.json").write_text("THIS IS NOT JSON {{{")
    return pantonicvideo_root


@pytest.fixture()
def root_with_missing_fields_layout(pantonicvideo_root):
    """Write a layout.json missing required fields."""
    (pantonicvideo_root / "layout.json").write_text(json.dumps({"version": 1}))
    return pantonicvideo_root


def test_unrecognized_version_falls_back_to_first_run(root_with_unknown_layout_version, app_runner):
    """S7 / §7.4 / §16.2: unrecognized layout.json version produces first-run layout."""
    result = app_runner(root=root_with_unknown_layout_version)
    assert result.is_first_run is True


def test_unrecognized_version_logs_warning(root_with_unknown_layout_version, app_runner):
    """S7 / §7.4: unrecognized layout.json version emits a WARNING to the infracore log."""
    result = app_runner(root=root_with_unknown_layout_version)
    assert any("layout" in w.lower() or "version" in w.lower() for w in result.warnings)


def test_malformed_layout_renamed(root_with_unknown_layout_version, pantonicvideo_root, app_runner):
    """S7 / §7.4: the unrecognized layout.json is renamed to layout.json.unrecognized-<timestamp>."""
    app_runner(root=root_with_unknown_layout_version)
    renamed = list(pantonicvideo_root.glob("layout.json.unrecognized-*"))
    assert len(renamed) == 1


def test_malformed_json_layout_triggers_first_run(root_with_malformed_layout, app_runner):
    """§7.4: malformed JSON in layout.json triggers first-run fallback."""
    result = app_runner(root=root_with_malformed_layout)
    assert result.is_first_run is True


def test_missing_fields_layout_triggers_first_run(root_with_missing_fields_layout, app_runner):
    """§7.4: layout.json missing required fields triggers first-run fallback."""
    result = app_runner(root=root_with_missing_fields_layout)
    assert result.is_first_run is True


def test_startup_is_healthy_after_mismatch(root_with_unknown_layout_version, app_runner):
    """§16.2: after layout fallback, the application is otherwise healthy."""
    result = app_runner(root=root_with_unknown_layout_version)
    assert result.startup_healthy is True
