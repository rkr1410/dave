"""Live session stream events."""

from __future__ import annotations

from dataclasses import dataclass

from dave.core.requests import ChatRequest


@dataclass
class StreamEvent:
    pass


@dataclass
class RequestBuilt(StreamEvent):
    request: ChatRequest


@dataclass
class RequestSent(StreamEvent):
    request: ChatRequest


@dataclass
class TextDelta(StreamEvent):
    text: str


@dataclass
class ReasoningDelta(StreamEvent):
    text: str


@dataclass
class ModelResponseFinished(StreamEvent):
    pass
