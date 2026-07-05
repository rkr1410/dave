"""Textual widgets for the initial chat surface."""

from __future__ import annotations

from textual.widgets import Input, Static

from dave.ui.textual.presenter import TranscriptItem


class ConversationView(Static):
    def render_items(self, items: tuple[TranscriptItem, ...]) -> None:
        if not items:
            self.update("")
            return

        self.update("\n\n".join(format_item(item) for item in items))


class PromptInput(Input):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(placeholder="Message Dave", **kwargs)


class StatusBar(Static):
    def render_status(self, status: str) -> None:
        self.update(status)


def format_item(item: TranscriptItem) -> str:
    label = {
        "user": "user",
        "assistant": "assistant",
        "reasoning": "thinking",
        "status": "status",
    }[item.role]

    suffix = "" if item.state == "done" else f" [{item.state}]"
    return f"{label}: {item.text}{suffix}"
