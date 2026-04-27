import uuid
from typing import Generic, NewType, Protocol, TypeVar

SubscriptionHandle = NewType("SubscriptionHandle", uuid.UUID)

T = TypeVar("T")


class Signal(Protocol[T]):
    @property
    def current_value(self) -> T: ...


class Subscription(Protocol):
    pass
