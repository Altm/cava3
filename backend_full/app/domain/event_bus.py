from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict


EventHandler = Callable[[Any], None]


class DomainEventBus:
    def __init__(self) -> None:
        self._handlers: DefaultDict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        handlers = self._handlers[event_type]
        if handler in handlers:
            return
        handlers.append(handler)

    def publish(self, event: Any) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def publish_many(self, events: list[Any]) -> None:
        for event in events:
            self.publish(event)


event_bus = DomainEventBus()


def subscribe(event_type: type):
    def decorator(func: EventHandler) -> EventHandler:
        event_bus.subscribe(event_type, func)
        return func

    return decorator
