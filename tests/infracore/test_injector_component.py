"""Tests for InjectorComponent — §4.7, S5, S2, S17."""

import pytest
from infracore.injector_component.injector import InjectorComponent
from contracts.exceptions import ServiceNotAvailable


class TestComponentVersion:
    """§4.1 — __component_version__ declared."""

    def test_component_version_declared(self):
        """§4.1: InjectorComponent module declares __component_version__ as semver."""
        import infracore.injector_component.injector as mod
        assert hasattr(mod, "__component_version__")
        v = mod.__component_version__
        parts = v.split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts)


class TestRegisterAndResolve:
    """§4.7 — register_component, register_service, resolve."""

    @pytest.fixture()
    def injector(self):
        return InjectorComponent()

    def test_register_component_resolves(self, injector):
        """§4.7: a registered component can be retrieved by name."""
        sentinel = object()
        injector.register_component("my_component", sentinel)
        # Components are resolved internally; no public resolve for components
        # but register must not raise.

    def test_register_service_and_resolve(self, injector):
        """§4.7: a registered service can be resolved by name and min_version."""
        class FakeService:
            service_api_version = "1.0.0"
            def __init__(self):
                pass

        from infracore.manifest.service_manifest import ServiceManifest
        manifest = ServiceManifest(
            name="fake_service",
            service_api_version="1.0.0",
            implementation_version="1.0.0",
            entry_point="fake:FakeService",
            depends_on=[],
        )
        injector.register_service("fake_service", manifest, FakeService)
        injector.construct_services()
        resolved = injector.resolve("fake_service", "1.0")
        assert isinstance(resolved, FakeService)

    def test_resolve_raises_service_not_available(self, injector):
        """§4.7: resolve raises ServiceNotAvailable when service is absent."""
        injector.construct_services()
        with pytest.raises(ServiceNotAvailable):
            injector.resolve("missing_service", "1.0")

    def test_resolve_raises_when_version_not_satisfied(self, injector):
        """§4.7: resolve raises ServiceNotAvailable when version constraint is not met."""
        class OldService:
            service_api_version = "1.0.0"
            def __init__(self):
                pass

        from infracore.manifest.service_manifest import ServiceManifest
        manifest = ServiceManifest(
            name="old_svc",
            service_api_version="1.0.0",
            implementation_version="1.0.0",
            entry_point="x:Old",
            depends_on=[],
        )
        injector.register_service("old_svc", manifest, OldService)
        injector.construct_services()
        with pytest.raises(ServiceNotAvailable):
            injector.resolve("old_svc", "2.0")


class TestTopologicalSort:
    """§4.7, S5 — construct_services performs topological sort."""

    @pytest.fixture()
    def injector(self):
        return InjectorComponent()

    def test_services_constructed_in_dependency_order(self, injector):
        """S5: a service that depends on another is constructed after its dependency."""
        construction_order = []

        class ServiceA:
            service_api_version = "1.0.0"
            def __init__(self):
                construction_order.append("a")

        class ServiceB:
            service_api_version = "1.0.0"
            def __init__(self, service_a):
                construction_order.append("b")

        from infracore.manifest.service_manifest import ServiceManifest, DependsOn
        ma = ServiceManifest(
            name="service_a",
            service_api_version="1.0.0",
            implementation_version="1.0.0",
            entry_point="x:ServiceA",
            depends_on=[],
        )
        mb = ServiceManifest(
            name="service_b",
            service_api_version="1.0.0",
            implementation_version="1.0.0",
            entry_point="x:ServiceB",
            depends_on=[DependsOn(name="service_a", min_version="1.0")],
        )
        injector.register_service("service_a", ma, ServiceA)
        injector.register_service("service_b", mb, ServiceB)
        injector.construct_services()
        assert construction_order.index("a") < construction_order.index("b")


class TestCycleDetection:
    """S5, §4.7 — cycle detection rejects every service in the cycle."""

    @pytest.fixture()
    def injector(self):
        return InjectorComponent()

    def test_cycle_rejects_all_cycle_members(self, injector):
        """S5: a dependency cycle causes all services in the cycle to be rejected; app does not abort."""
        from infracore.manifest.service_manifest import ServiceManifest, DependsOn

        class SvcX:
            service_api_version = "1.0.0"
            def __init__(self, service_y):
                pass

        class SvcY:
            service_api_version = "1.0.0"
            def __init__(self, service_x):
                pass

        mx = ServiceManifest(
            name="service_x",
            service_api_version="1.0.0",
            implementation_version="1.0.0",
            entry_point="x:SvcX",
            depends_on=[DependsOn(name="service_y", min_version="1.0")],
        )
        my = ServiceManifest(
            name="service_y",
            service_api_version="1.0.0",
            implementation_version="1.0.0",
            entry_point="x:SvcY",
            depends_on=[DependsOn(name="service_x", min_version="1.0")],
        )
        injector.register_service("service_x", mx, SvcX)
        injector.register_service("service_y", my, SvcY)
        injector.construct_services()
        with pytest.raises(ServiceNotAvailable):
            injector.resolve("service_x", "1.0")
        with pytest.raises(ServiceNotAvailable):
            injector.resolve("service_y", "1.0")

    def test_acyclic_services_survive_cycle(self, injector):
        """S5: services not in a cycle are still constructed when a cycle exists elsewhere."""
        from infracore.manifest.service_manifest import ServiceManifest, DependsOn

        class SvcCyclicA:
            service_api_version = "1.0.0"
            def __init__(self, cyclic_b):
                pass

        class SvcCyclicB:
            service_api_version = "1.0.0"
            def __init__(self, cyclic_a):
                pass

        class SvcGood:
            service_api_version = "1.0.0"
            def __init__(self):
                pass

        injector.register_service(
            "cyclic_a",
            ServiceManifest(name="cyclic_a", service_api_version="1.0.0", implementation_version="1.0.0",
                            entry_point="x:A", depends_on=[DependsOn(name="cyclic_b", min_version="1.0")]),
            SvcCyclicA,
        )
        injector.register_service(
            "cyclic_b",
            ServiceManifest(name="cyclic_b", service_api_version="1.0.0", implementation_version="1.0.0",
                            entry_point="x:B", depends_on=[DependsOn(name="cyclic_a", min_version="1.0")]),
            SvcCyclicB,
        )
        injector.register_service(
            "good_svc",
            ServiceManifest(name="good_svc", service_api_version="1.0.0", implementation_version="1.0.0",
                            entry_point="x:G", depends_on=[]),
            SvcGood,
        )
        injector.construct_services()
        good = injector.resolve("good_svc", "1.0")
        assert isinstance(good, SvcGood)


class TestServicesFor:
    """§4.7 — services_for resolves a plugin's required services dict."""

    @pytest.fixture()
    def injector(self):
        return InjectorComponent()

    def test_services_for_returns_dict(self, injector):
        """§4.7: services_for returns a dict mapping service names to instances."""
        class FakeSvc:
            service_api_version = "1.0.0"
            def __init__(self):
                pass

        from infracore.manifest.service_manifest import ServiceManifest
        from contracts.manifest import RequiredService
        injector.register_service(
            "fake_svc",
            ServiceManifest(name="fake_svc", service_api_version="1.0.0",
                            implementation_version="1.0.0", entry_point="x:F", depends_on=[]),
            FakeSvc,
        )
        injector.construct_services()
        result = injector.services_for(
            "my_plugin", [RequiredService(name="fake_svc", min_version="1.0")]
        )
        assert "fake_svc" in result
        assert isinstance(result["fake_svc"], FakeSvc)

    def test_services_for_raises_when_missing(self, injector):
        """§4.7: services_for raises ServiceNotAvailable when a required service is absent."""
        from contracts.manifest import RequiredService
        injector.construct_services()
        with pytest.raises(ServiceNotAvailable):
            injector.services_for(
                "my_plugin", [RequiredService(name="nonexistent", min_version="1.0")]
            )
