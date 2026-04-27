from __future__ import annotations

import uuid
from typing import Any, Callable

from infracore.bootstrap_components.signal_component.handle import SubscriptionHandle

__component_version__ = "1.0.0"


class Signal:
    def __init__(self, initial: Any, register: Callable) -> None:
        self._current = initial
        self._callbacks: list[Callable] = []
        # register is the source's push mechanism; call it with our feed function
        def _feed(value: Any) -> None:
            self._current = value
            for cb in list(self._callbacks):
                cb(value)
        try:
            register(_feed)
        except Exception:
            pass

    @property
    def current_value(self) -> Any:
        return self._current


class SignalComponent:
    def __init__(self) -> None:
        self._subscriptions: dict[uuid.UUID, list] = {}

    def make_signal(self, initial: Any, register: Callable) -> Signal:
        return Signal(initial, register)

    def subscribe(self, sig: Signal, callback: Callable) -> SubscriptionHandle:
        sub_id = uuid.uuid4()
        enabled: list[bool] = [True]

        def guarded(value: Any) -> None:
            if enabled[0]:
                callback(value)

        sig._callbacks.append(guarded)
        self._subscriptions[sub_id] = enabled
        return sub_id  # type: ignore[return-value]

    def unsubscribe(self, handle: SubscriptionHandle) -> None:
        sub_id = handle  # NewType is identity at runtime
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id][0] = False
