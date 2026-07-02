"""Message materialization primitives."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from dave.core.events import AssistantMessageAppended, Event, UserMessageAppended
from dave.core.tool_calls import ToolCall

MessageRole = Literal["system", "developer", "user", "assistant", "tool"]


@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


def materialize_messages(events: Iterable[Event]) -> tuple[Message, ...]:
    messages: list[Message] = []

    for event in events:
        if isinstance(event, UserMessageAppended):
            messages.append(Message(role="user", content=event.content))
        elif isinstance(event, AssistantMessageAppended):
            messages.append(
                Message(
                    role="assistant",
                    content=event.content,
                    tool_calls=deepcopy(event.tool_calls),
                )
            )

    return tuple(messages)
