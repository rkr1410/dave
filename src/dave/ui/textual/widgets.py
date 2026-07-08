"""Textual widgets for the initial chat surface."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.widgets import Input, RichLog, Static

from dave.ui.textual.presenter import TranscriptItem
from dave.ui.textual import theme

TOGGLE_REASONING_META = "toggle_reasoning_index"


class ConversationView(RichLog):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(
            wrap=True,
            highlight=False,
            markup=False,
            auto_scroll=True,
            min_width=1,
            **kwargs,
        )
        self._items: tuple[TranscriptItem, ...] = ()
        self._collapsed_reasoning_indices: set[int] = set()
        self._manually_expanded_reasoning_indices: set[int] = set()
        self._reasoning_pulse_phase = 0
        self._reasoning_pulse_timer = None

    def on_mount(self) -> None:
        self._reasoning_pulse_timer = self.set_interval(
            0.5,
            self._tick_reasoning_pulse,
            name="reasoning pulse",
            pause=True,
        )

    def render_items(self, items: tuple[TranscriptItem, ...]) -> None:
        self._items = items
        self._collapse_new_reasoning_items()
        self._prune_collapsed_reasoning_indices()
        self._sync_reasoning_pulse_timer()
        previous_scroll_y = self.scroll_y
        should_auto_scroll = self._should_auto_scroll()

        self.clear()

        if not items:
            return

        transcript = Text()
        for index, item in enumerate(items):
            if index > 0:
                transcript.append("\n\n")
            transcript.append(
                format_item(
                    item,
                    index=index,
                    collapsed=index in self._collapsed_reasoning_indices,
                    pulse_phase=self._pulse_phase_for_item(item),
                )
            )

        self.write(transcript, scroll_end=should_auto_scroll, animate=False)

        if not should_auto_scroll:
            self.scroll_to(y=previous_scroll_y, animate=False, immediate=True)

    def _on_click(self, event: events.Click) -> None:
        index = event.style.meta.get(TOGGLE_REASONING_META)
        if not isinstance(index, int):
            return

        if index in self._collapsed_reasoning_indices:
            self._collapsed_reasoning_indices.remove(index)
            self._manually_expanded_reasoning_indices.add(index)
        else:
            self._collapsed_reasoning_indices.add(index)
            self._manually_expanded_reasoning_indices.discard(index)

        self.render_items(self._items)
        event.stop()

    def _should_auto_scroll(self) -> bool:
        if self.max_scroll_y <= 0:
            return True
        return self.scroll_y >= self.max_scroll_y

    def _prune_collapsed_reasoning_indices(self) -> None:
        reasoning_indices = {
            index
            for index, item in enumerate(self._items)
            if item.role == "reasoning"
        }
        self._collapsed_reasoning_indices.intersection_update(reasoning_indices)
        self._manually_expanded_reasoning_indices.intersection_update(reasoning_indices)

    def _collapse_new_reasoning_items(self) -> None:
        for index, item in enumerate(self._items):
            if item.role != "reasoning":
                continue
            if index in self._manually_expanded_reasoning_indices:
                continue
            self._collapsed_reasoning_indices.add(index)

    def _has_streaming_reasoning(self) -> bool:
        return any(
            item.role == "reasoning" and item.state == "streaming"
            for item in self._items
        )

    def _pulse_phase_for_item(self, item: TranscriptItem) -> int | None:
        if item.role == "reasoning" and item.state == "streaming":
            return self._reasoning_pulse_phase
        return None

    def _sync_reasoning_pulse_timer(self) -> None:
        if self._reasoning_pulse_timer is None:
            return

        if self._has_streaming_reasoning():
            self._reasoning_pulse_timer.resume()
        else:
            self._reasoning_pulse_timer.pause()
            self._reasoning_pulse_phase = 0

    def _tick_reasoning_pulse(self) -> None:
        if not self._has_streaming_reasoning():
            self._sync_reasoning_pulse_timer()
            return

        self._reasoning_pulse_phase = (
            self._reasoning_pulse_phase + 1
        ) % len(theme.REASONING_LABEL_PULSE_STYLES)
        self.render_items(self._items)


class PromptInput(Input):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(placeholder="Message Dave", **kwargs)


class StatusBar(Static):
    def render_status(self, status: str) -> None:
        self.update(format_status(status))


def format_item(
    item: TranscriptItem,
    *,
    index: int | None = None,
    collapsed: bool = False,
    pulse_phase: int | None = None,
) -> Text:
    text = Text()
    label = format_label(item, collapsed=collapsed)
    label_start = len(text)
    text.append(label, style=label_style(item, pulse_phase=pulse_phase))

    if item.role == "reasoning" and index is not None:
        text.apply_meta(
            {TOGGLE_REASONING_META: index},
            start=label_start,
            end=label_start + len(label),
        )

    if collapsed and item.role == "reasoning":
        text.append("[collapsed]", style=theme.CANCELLED_CONTENT)
    else:
        text.append(item.text, style=content_style(item))

    if item.state != "done":
        text.append(f" [{item.state}]", style=state_style(item))

    return text


def format_label(item: TranscriptItem, *, collapsed: bool = False) -> str:
    if item.role == "reasoning":
        marker = "+" if collapsed else "-"
        return f"thinking[{marker}]: "

    return {
        "user": "you: ",
        "assistant": "dave: ",
        "status": "status: ",
    }[item.role]


def label_style(item: TranscriptItem, *, pulse_phase: int | None = None) -> str:
    if pulse_phase is not None and item.role == "reasoning":
        return theme.REASONING_LABEL_PULSE_STYLES[
            pulse_phase % len(theme.REASONING_LABEL_PULSE_STYLES)
        ]

    return {
        "user": theme.USER_LABEL,
        "assistant": theme.ASSISTANT_LABEL,
        "reasoning": theme.REASONING_LABEL,
        "status": theme.STATUS_LABEL,
    }[item.role]


def content_style(item: TranscriptItem) -> str:
    if item.state == "cancelled":
        return theme.CANCELLED_CONTENT
    if item.state == "failed":
        return theme.FAILED_CONTENT
    if item.role == "reasoning":
        return theme.REASONING_CONTENT
    return ""


def state_style(item: TranscriptItem) -> str:
    return {
        "streaming": theme.STREAMING_STATE,
        "done": "",
        "failed": theme.FAILED_STATE,
        "cancelled": theme.CANCELLED_STATE,
    }[item.state]


def format_status(status: str) -> Text:
    text = Text()
    text.append("status: ", style=theme.STATUS_TEXT_LABEL)
    text.append(status, style=status_style(status))
    return text


def status_style(status: str) -> str:
    if status in {"failed", "request rejected"}:
        return theme.STATUS_FAILED
    if status == "cancelled":
        return theme.STATUS_CANCELLED
    if status in {"streaming", "requesting", "request built", "request approved"}:
        return theme.STATUS_ACTIVE
    return theme.STATUS_IDLE
