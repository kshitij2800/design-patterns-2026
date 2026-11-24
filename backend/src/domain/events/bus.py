from collections import defaultdict
from collections.abc import Callable
from typing import Any

Handler = Callable[[Any], None]


class EventBus:
    """In-process publish/subscribe (the Observer subject).

    Publishers only know publish(); they never know who listens.
    Handlers for one event class run in subscription order. No unsubscribe.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: object) -> None:
        for handler in list(self._handlers.get(type(event), ())):
            handler(event)