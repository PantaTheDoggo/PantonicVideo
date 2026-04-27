import uuid
from typing import NewType

SubscriptionHandle = NewType("SubscriptionHandle", uuid.UUID)
