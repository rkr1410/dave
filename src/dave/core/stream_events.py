"""Live session stream events."""

from __future__ import annotations

from dataclasses import dataclass

from dave.core.requests import ModelRequest


@dataclass
class StreamEvent:
    pass


@dataclass
class RequestBuilt(StreamEvent):
    request: ModelRequest


@dataclass
class RequestSent(StreamEvent):
    request: ModelRequest


@dataclass
class TextDelta(StreamEvent):
    text: str


@dataclass
class ReasoningDelta(StreamEvent):
    text: str


@dataclass
class ModelResponseFinished(StreamEvent):
    pass
