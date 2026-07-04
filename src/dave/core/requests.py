"""Provider-neutral chat request primitives."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from dave.core.messages import Message


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    messages: tuple[Message, ...]


@dataclass
class Approve:
    request: ChatRequest


@dataclass
class Reject:
    reason: str
