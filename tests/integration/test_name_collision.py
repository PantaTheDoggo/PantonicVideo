"""Integration test — §16.2 scenario 5: built-in / third-party name collision."""

import json

import pytest


@pytest.fixture()
def root_with_third_party_collision(pantonicvideo_root):
    """Place a third-party plugin with the same name as a built-in (project_launcher)."""
    plugin_dir = pantonicvideo_root / "plugins" / "project_launcher"
    plugin_dir.mkdir()
    manifest = {
        "name": "project_launcher",
        "version": "2.0.0",
        "contracts_min_version": "1.0",
        "author": "ThirdParty",
        "description": "A third-party override — should be rejected.",
        "entry_point": "plugin:FakeProjectLauncher",
        "required_services": [],
        "inputs": [],
        "outputs": [],
        "permissions": [],
    }
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
    (plugin_dir / "plugin.py").write_text(
        "class FakeProjectLauncher:\n"
        "    def on_load(self, services): pass\n"
        "    def on_enable(self): pass\n"
        "    def on_disable(self): pass\n"
        "    def on_unload(self): pass\n"
    )
    return pantonicvideo_root


def test_builtin_wins_on_collision(root_with_third_party_collision, app_runner):
    """S6 / §9.7 / §16.2: built-in project_launcher is enabled; third-party is failed."""
    result = app_runner(root=root_with_third_party_collision)
    builtin = next(
        (p for p in result.plugin_records if p.name == "project_launcher" and p.is_builtin),
        None,
    )
    assert builtin is not None
    assert builtin.status in ("enabled", "loaded")


def test_third_party_collision_marked_failed(root_with_third_party_collision, app_runner):
    """S6 / §9.7 / §16.2: the third-party plugin with a colliding name is marked 'failed'."""
    result = app_runner(root=root_with_third_party_collision)
    third_party = next(
        (p for p in result.plugin_records if p.name == "project_launcher" and not p.is_builtin),
        None,
    )
    assert third_party is not None
    assert third_party.status == "failed"
    assert "collides" in third_party.failure_reason.lower() or "built-in" in third_party.failure_reason.lower()


def test_collision_logged_at_error(root_with_third_party_collision, app_runner):
    """S6 / §9.7: the name collision is logged at ERROR level."""
    result = app_runner(root=root_with_third_party_collision)
    assert any(
        "project_launcher" in e.lower() and "collide" in e.lower()
        for e in result.errors
    )


def test_collision_does_not_abort_startup(root_with_third_party_collision, app_runner):
    """S6 / §16.2: the name collision does not abort startup; the app is otherwise healthy."""
    result = app_runner(root=root_with_third_party_collision)
    assert result.startup_healthy is True


def test_builtin_plugin_enabled_per_persisted_state(root_with_third_party_collision, pantonicvideo_root, app_runner):
    """S6 / §9.11: the built-in plugin's enabled state comes from the persisted state, not the third-party."""
    state = {"plugins.project_launcher.enabled": True}
    (pantonicvideo_root / "state.json").write_text(json.dumps(state))
    (pantonicvideo_root / "layout.json").write_text(
        json.dumps({"version": 1, "saved_at": "2026-01-01T00:00:00Z", "qt_state": ""})
    )
    result = app_runner(root=root_with_third_party_collision)
    builtin = next(
        (p for p in result.plugin_records if p.name == "project_launcher" and p.is_builtin),
        None,
    )
    assert builtin is not None
    assert builtin.status == "enabled"
