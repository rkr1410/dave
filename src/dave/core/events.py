"""Canonical session events."""

from __future__ import annotations

from dataclasses import dataclass

from dave.core.artifacts import ArtifactRef
from dave.core.tool_calls import ToolCall


@dataclass(kw_only=True)
class Event:
    id: str | None = None
    parent_id: str | None = None


@dataclass
class SystemPromptSet(Event):
    content: str


@dataclass
class UserMessageAppended(Event):
    content: str


@dataclass
class RequestApproved(Event):
    request_ref: ArtifactRef
    model: str
    message_count: int


@dataclass
class RequestRejected(Event):
    reason: str


@dataclass
class AssistantMessageAppended(Event):
    content: str
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass
class ToolResultAppended(Event):
    tool_call_id: str
    result_ref: ArtifactRef


@dataclass
class ModelResponseFailed(Event):
    error_ref: ArtifactRef
    partial_output_ref: ArtifactRef | None = None
