"""Message materialization primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dave.core.tool_calls import ToolCall

MessageRole = Literal["system", "developer", "user", "assistant", "tool"]


@dataclass
class Message:
    role: MessageRole
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
