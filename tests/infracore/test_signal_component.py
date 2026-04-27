"""Tests for SignalComponent — §4.2, §4.1."""

import pytest
from infracore.bootstrap_components.signal_component.signal import SignalComponent
from infracore.bootstrap_components.signal_component.handle import SubscriptionHandle


class TestComponentVersion:
    """§4.1 — every component module declares __component_version__."""

    def test_component_version_declared(self):
        """§4.1: SignalComponent module exposes __component_version__ as a semver string."""
        import infracore.bootstrap_components.signal_component.signal as mod
        assert hasattr(mod, "__component_version__")
        version = mod.__component_version__
        assert isinstance(version, str)
        parts = version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestMakeSignal:
    """§4.2 — make_signal creates a Signal[T] with the given initial value."""

    def test_make_signal_returns_signal(self):
        """§4.2: make_signal returns a Signal object with the initial value cached."""
        component = SignalComponent()
        received = []

        def register(cb):
            return SubscriptionHandle.__supertype__(
                __import__("uuid").uuid4()
            )

        sig = component.make_signal(initial=42, register=register)
        assert sig is not None

    def test_make_signal_caches_initial_value(self):
        """§4.2: Signal caches latest emitted value for synchronous reads."""
        component = SignalComponent()
        received = []

        def register(cb):
            received.append(cb)
            return SubscriptionHandle.__supertype__(
                __import__("uuid").uuid4()
            )

        sig = component.make_signal(initial="hello", register=register)
        assert sig.current_value == "hello"


class TestSubscribeUnsubscribe:
    """§4.2 — subscribe / unsubscribe round-trip."""

    def test_subscribe_receives_emissions(self):
        """§4.2: callback registered via subscribe is invoked when the underlying source emits."""
        component = SignalComponent()
        fired = []
        callbacks = []

        def register(cb):
            callbacks.append(cb)
            import uuid
            return SubscriptionHandle.__supertype__(uuid.uuid4())

        sig = component.make_signal(initial=0, register=register)
        sub = component.subscribe(sig, fired.append)
        callbacks[0](99)
        assert 99 in fired

    def test_unsubscribe_stops_callbacks(self):
        """§4.2: unsubscribe prevents the callback from being called on future emissions."""
        component = SignalComponent()
        fired = []
        callbacks = []

        def register(cb):
            callbacks.append(cb)
            import uuid
            return SubscriptionHandle.__supertype__(uuid.uuid4())

        sig = component.make_signal(initial=0, register=register)
        sub = component.subscribe(sig, fired.append)
        component.unsubscribe(sub)
        callbacks[0](55)
        assert 55 not in fired

    def test_no_polling_pattern(self):
        """§4.2: Signal abstraction is the only observation idiom — no polling."""
        component = SignalComponent()
        assert not hasattr(component, "poll")
        assert not hasattr(component, "get_value")
