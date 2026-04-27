from __future__ import annotations

from typing import Any, Callable, Optional


def call_on_load(
    plugin: Any,
    services: dict[str, Any],
    plugin_name: Optional[str] = None,
    on_failure: Optional[Callable[[str, str], None]] = None,
) -> None:
    """Call plugin.on_load(services). Validate all lifecycle hooks exist first."""
    required_hooks = ["on_load", "on_enable", "on_disable", "on_unload"]
    for hook in required_hooks:
        if not hasattr(plugin, hook):
            if on_failure and plugin_name:
                on_failure(plugin_name, f"lifecycle hook not implemented: {hook}")
            return
    try:
        plugin.on_load(services)
    except Exception as exc:
        if on_failure and plugin_name:
            on_failure(plugin_name, str(exc))


def call_on_enable(
    plugin: Any,
    plugin_name: Optional[str] = None,
    on_failure: Optional[Callable[[str, str], None]] = None,
) -> None:
    try:
        plugin.on_enable()
    except Exception as exc:
        if on_failure and plugin_name:
            on_failure(plugin_name, str(exc))


def call_on_disable(
    plugin: Any,
    plugin_name: Optional[str] = None,
    on_failure: Optional[Callable[[str, str], None]] = None,
) -> None:
    try:
        plugin.on_disable()
    except Exception as exc:
        if on_failure and plugin_name:
            on_failure(plugin_name, str(exc))


def call_on_unload(
    plugin: Any,
    plugin_name: Optional[str] = None,
    on_failure: Optional[Callable[[str, str], None]] = None,
) -> None:
    try:
        plugin.on_unload()
    except Exception as exc:
        if on_failure and plugin_name:
            on_failure(plugin_name, str(exc))


def resolve_enabled_on_first_run(
    plugin_name: str,
    app_state: Any,
    is_first_run: bool,
) -> bool:
    """§9.11: on first run, project_launcher is always enabled; others honour persisted state."""
    if is_first_run and plugin_name == "project_launcher":
        return True
    persisted = app_state.state_get(f"plugins.{plugin_name}.enabled")
    return bool(persisted) if persisted is not None else False
