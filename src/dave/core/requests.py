"""Provider-neutral chat request primitives."""

from __future__ import annotations

from dataclasses import dataclass

from dave.core.messages import Message


@dataclass
class ChatRequest:
    model: str
    messages: tuple[Message, ...]


@dataclass
class Approve:
    request: ChatRequest


@dataclass
class Reject:
    reason: str
