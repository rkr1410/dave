"""Message materialization primitives."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from dave.core.events import AssistantMessageAppended, Event, UserMessageAppended
from dave.core.tool_calls import ToolCall

class MessageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SystemMessage(MessageModel):
    role: Literal["system"] = "system"
    content: str


class DeveloperMessage(MessageModel):
    role: Literal["developer"] = "developer"
    content: str


class UserMessage(MessageModel):
    role: Literal["user"] = "user"
    content: str


class AssistantMessage(MessageModel):
    role: Literal["assistant"] = "assistant"
    content: str
    tool_calls: tuple[ToolCall, ...] = ()


class ToolMessage(MessageModel):
    role: Literal["tool"] = "tool"
    content: str
    tool_call_id: str


Message = Annotated[
    SystemMessage | DeveloperMessage | UserMessage | AssistantMessage | ToolMessage,
    Field(discriminator="role"),
]


def materialize_messages(events: Iterable[Event]) -> tuple[Message, ...]:
    messages: list[Message] = []

    for event in events:
        if isinstance(event, UserMessageAppended):
            messages.append(UserMessage(content=event.content))
        elif isinstance(event, AssistantMessageAppended):
            messages.append(
                AssistantMessage(
                    content=event.content,
                    tool_calls=deepcopy(event.tool_calls),
                )
            )

    return tuple(messages)
