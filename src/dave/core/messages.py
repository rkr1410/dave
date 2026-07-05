"""Message materialization primitives."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from dave.core.events import (
    AssistantMessageAppended,
    Event,
    SystemPromptSet,
    UserMessageAppended,
)
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
    system_prompt: str | None = None

    for event in events:
        match event:
            case SystemPromptSet():
                system_prompt = event.content
            case UserMessageAppended():
                messages.append(UserMessage(content=event.content))
            case AssistantMessageAppended():
                messages.append(
                    AssistantMessage(
                        content=event.content,
                        tool_calls=deepcopy(event.tool_calls),
                    )
                )

    if system_prompt is None:
        return tuple(messages)

    return SystemMessage(content=system_prompt), *messages
