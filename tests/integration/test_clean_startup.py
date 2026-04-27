"""Integration test — §16.2 scenario 1: clean startup with three built-in plugins."""

import pytest


def test_clean_startup_project_launcher_enabled(app_runner, pantonicvideo_root):
    """§16.2: clean startup enables Project Launcher; Image Cropping and Subtitle Text Tool are loaded but not enabled."""
    result = app_runner()
    assert result.project_launcher_status == "enabled"
    assert result.image_cropping_status == "loaded"
    assert result.subtitle_text_tool_status == "loaded"


def test_clean_startup_no_alerts(app_runner, pantonicvideo_root):
    """§16.2: clean startup produces no alerts in the alert sink."""
    result = app_runner()
    assert result.alert_count == 0


def test_clean_startup_nine_services_registered(app_runner, pantonicvideo_root):
    """§9.8: clean startup reaches the UI shell with all nine services constructed."""
    result = app_runner()
    assert result.service_count == 9


def test_clean_startup_logs_infracore_log(app_runner, pantonicvideo_root):
    """§9.2: clean startup writes to <root>/logs/infracore.log."""
    app_runner()
    log_file = pantonicvideo_root / "logs" / "infracore.log"
    assert log_file.exists()


def test_clean_startup_shutdown_clean(app_runner, pantonicvideo_root):
    """§9.13: clean shutdown calls on_disable and on_unload for all plugins; saves layout."""
    result = app_runner()
    assert result.shutdown_clean is True
    layout_file = pantonicvideo_root / "layout.json"
    assert layout_file.exists()
