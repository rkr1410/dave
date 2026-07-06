"""Map runtime events to UI transcript state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dave.runtime.events import (
    AssistantMessageAppended,
    Event,
    ModelResponseFailed,
    RequestApproved,
    RequestRejected,
    UserMessageAppended,
)
from dave.runtime.stream_events import (
    ModelResponseFinished,
    ReasoningDelta,
    RequestBuilt,
    RequestSent,
    StreamEvent,
    TextDelta,
)

TranscriptRole = Literal["user", "assistant", "reasoning", "status"]
TranscriptState = Literal["streaming", "done", "failed", "cancelled"]


@dataclass
class TranscriptItem:
    role: TranscriptRole
    text: str
    state: TranscriptState = "done"


class ConversationPresenter:
    def __init__(self) -> None:
        self._items: list[TranscriptItem] = []
        self._active_reasoning_index: int | None = None
        self._active_assistant_index: int | None = None
        self.status = "idle"

    @property
    def items(self) -> tuple[TranscriptItem, ...]:
        return tuple(self._items)

    def apply(self, event: Event | StreamEvent) -> None:
        match event:
            case UserMessageAppended():
                self._items.append(TranscriptItem("user", event.content))
                self.status = "requesting"
            case RequestBuilt():
                self.status = "request built"
            case RequestApproved():
                self.status = "request approved"
            case RequestRejected():
                self._items.append(
                    TranscriptItem("status", f"request rejected: {event.reason}", "failed")
                )
                self.status = "request rejected"
            case RequestSent():
                self.status = "streaming"
            case ReasoningDelta():
                self._append_reasoning(event.text)
            case TextDelta():
                self._append_assistant(event.text)
            case ModelResponseFinished():
                self._mark_active_items("done")
                self.status = "finishing"
            case AssistantMessageAppended():
                self._finish_assistant(event.content)
                self.status = "idle"
            case ModelResponseFailed():
                self._mark_active_items("failed")
                self._clear_active_items()
                self._items.append(
                    TranscriptItem("status", "model response failed", "failed")
                )
                self.status = "failed"

    def cancel_active_response(self) -> None:
        self._mark_active_items("cancelled")
        self._clear_active_items()
        self.status = "cancelled"

    def _append_reasoning(self, text: str) -> None:
        index = self._active_reasoning_index
        if index is None:
            index = len(self._items)
            self._active_reasoning_index = index
            self._items.append(TranscriptItem("reasoning", "", "streaming"))

        item = self._items[index]
        item.text += text

    def _append_assistant(self, text: str) -> None:
        index = self._active_assistant_index
        if index is None:
            index = len(self._items)
            self._active_assistant_index = index
            self._items.append(TranscriptItem("assistant", "", "streaming"))

        item = self._items[index]
        item.text += text

    def _finish_assistant(self, content: str) -> None:
        self._mark_active_items("done")

        index = self._active_assistant_index
        if index is None:
            self._items.append(TranscriptItem("assistant", content))
        else:
            item = self._items[index]
            item.text = content
            item.state = "done"

        self._clear_active_items()

    def _mark_active_items(self, state: TranscriptState) -> None:
        for index in (self._active_reasoning_index, self._active_assistant_index):
            if index is not None:
                self._items[index].state = state

    def _clear_active_items(self) -> None:
        self._active_reasoning_index = None
        self._active_assistant_index = None
