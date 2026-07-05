"""In-memory canonical event log."""

from __future__ import annotations

from copy import deepcopy
from typing import TypeVar

from dave.core.events import Event

EventT = TypeVar("EventT", bound=Event)


class EventLog:
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._next_number = 1

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(deepcopy(event) for event in self._events)

    def append(self, event: EventT) -> EventT:
        stored_event = deepcopy(event)
        stored_event.id = self._next_id()
        stored_event.parent_id = self._events[-1].id if self._events else None
        self._events.append(stored_event)
        return deepcopy(stored_event)

    def _next_id(self) -> str:
        event_id = f"event-{self._next_number}"
        self._next_number += 1
        return event_id
