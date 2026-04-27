from __future__ import annotations

import inspect
from collections import defaultdict, deque
from typing import Any

from contracts.exceptions import ServiceNotAvailable
from contracts.manifest import RequiredService
from infracore.manifest.service_manifest import ServiceManifest
from infracore.version_check import caret_match, normalize_version

__component_version__ = "1.0.0"


class InjectorComponent:
    def __init__(self) -> None:
        self._components: dict[str, Any] = {}
        self._service_registry: dict[str, tuple[ServiceManifest, type]] = {}
        self._instances: dict[str, Any] = {}
        self._failed: set[str] = set()

    def register_component(self, name: str, instance: Any) -> None:
        self._components[name] = instance

    def register_service(self, name: str, manifest: ServiceManifest, cls: type) -> None:
        self._service_registry[name] = (manifest, cls)

    def construct_services(self) -> None:
        """Topological sort + construct; detect cycles; surviving services are instantiated."""
        names = list(self._service_registry.keys())
        in_degree: dict[str, int] = {n: 0 for n in names}
        dependents: dict[str, list[str]] = defaultdict(list)

        for name, (manifest, _) in self._service_registry.items():
            for dep in manifest.depends_on:
                if dep.name in self._service_registry:
                    in_degree[name] += 1
                    dependents[dep.name].append(name)

        queue: deque[str] = deque(n for n in names if in_degree[n] == 0)
        topo_order: list[str] = []
        while queue:
            node = queue.popleft()
            topo_order.append(node)
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        cyclic = {n for n in names if n not in topo_order}
        self._failed.update(cyclic)

        for name in topo_order:
            manifest, cls = self._service_registry[name]
            kwargs: dict[str, Any] = {}
            dep_failed = False
            for dep in manifest.depends_on:
                if dep.name in self._failed or dep.name not in self._instances:
                    dep_failed = True
                    break
                kwargs[dep.name] = self._instances[dep.name]
            if dep_failed:
                self._failed.add(name)
                continue
            # Inject component dependencies: constructor params named
            # "{comp_key}_component" are matched to registered components.
            try:
                sig = inspect.signature(cls.__init__)
                for param_name in sig.parameters:
                    if param_name == "self" or param_name in kwargs:
                        continue
                    for comp_key, comp_instance in self._components.items():
                        if param_name == f"{comp_key}_component":
                            kwargs[param_name] = comp_instance
                            break
            except (ValueError, TypeError):
                pass
            try:
                instance = cls(**kwargs)
                # Stamp service_api_version so resolve() can check version constraints.
                if not hasattr(instance, "service_api_version"):
                    instance.service_api_version = manifest.service_api_version
                self._instances[name] = instance
            except Exception:
                self._failed.add(name)

    def resolve(self, name: str, min_version: str) -> Any:
        if name in self._failed or name not in self._instances:
            raise ServiceNotAvailable(f"Service '{name}' is not available")
        instance = self._instances[name]
        svc_version = normalize_version(getattr(instance, "service_api_version", "0.0.0"))
        if not caret_match(f"^{min_version}", svc_version):
            raise ServiceNotAvailable(
                f"Service '{name}' version {svc_version} does not satisfy ^{min_version}"
            )
        return instance

    def services_for(self, plugin_name: str, required: list[RequiredService]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for req in required:
            result[req.name] = self.resolve(req.name, req.min_version)
        return result
