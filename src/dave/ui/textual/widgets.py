"""Textual widgets for the initial chat surface."""

from __future__ import annotations

from textual.widgets import Input, RichLog, Static

from dave.ui.textual.presenter import TranscriptItem


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

    def render_items(self, items: tuple[TranscriptItem, ...]) -> None:
        self.clear()

        if not items:
            return

        self.write(
            "\n\n".join(format_item(item) for item in items),
            scroll_end=True,
            animate=False,
        )


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
