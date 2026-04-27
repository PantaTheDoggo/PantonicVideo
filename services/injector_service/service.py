from __future__ import annotations

from contracts.exceptions import ServiceNotAvailable


class InjectorServiceImpl:
    def __init__(self, injector_component: object) -> None:
        self._comp = injector_component

    def resolve(self, name: str, min_version: str) -> object:
        return self._comp.resolve(name, min_version)
