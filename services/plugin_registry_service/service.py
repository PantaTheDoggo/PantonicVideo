from __future__ import annotations

from typing import Any


class PluginRegistryServiceImpl:
    def __init__(
        self,
        plugin_registry_component: object,
        signal_service: object,
        app_state_service: object,
    ) -> None:
        self._comp = plugin_registry_component
        self._signal_service = signal_service
        self._app_state_service = app_state_service

    def list_plugins(self) -> list:
        return self._comp.list_plugins()

    def enable(self, name: str) -> None:
        self._app_state_service.set(f"plugins.{name}.enabled", True)

    def disable(self, name: str) -> None:
        self._app_state_service.set(f"plugins.{name}.enabled", False)

    def observe_plugins(self) -> Any:
        return self._signal_service.signal_for_plugins()
