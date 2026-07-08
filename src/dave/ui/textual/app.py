"""Textual app skeleton for Dave."""

from __future__ import annotations

import asyncio
from collections import deque

from textual.app import App, ComposeResult
from textual.widgets import Input

from dave.runtime.session import Session
from dave.ui.textual import theme
from dave.ui.textual.presenter import ConversationPresenter
from dave.ui.textual.widgets import ConversationView, PromptInput, StatusBar


class DaveTextualApp(App[None]):
    CSS = f"""
    Screen {{
        layout: vertical;
        background: {theme.BACKGROUND};
        color: {theme.TEXT};
    }}

    ConversationView {{
        height: 1fr;
        min-height: 0;
        padding: 1;
        background: {theme.PANEL};
        background-tint: 0%;
        color: {theme.TEXT};
        border: solid {theme.PANEL_BORDER};
        overflow-x: hidden;
        overflow-y: scroll;
        scrollbar-visibility: hidden;
    }}

    ConversationView:focus {{
        background: {theme.PANEL};
        background-tint: 0%;
    }}

    StatusBar {{
        height: 1;
        padding: 0 1;
        background: {theme.BACKGROUND};
        color: {theme.MUTED};
    }}

    PromptInput {{
        height: 3;
        padding: 0 1;
        background: {theme.PANEL};
        background-tint: 0%;
        opacity: 1;
        text-opacity: 1;
        color: {theme.TEXT};
        border: none;
        border-top: solid {theme.INPUT_BORDER};
    }}

    PromptInput:focus {{
        background: {theme.PANEL};
        background-tint: 0%;
        border: none;
        border-top: solid {theme.INPUT_BORDER};
    }}

    PromptInput:disabled {{
        padding: 0 1;
        background: {theme.PANEL};
        background-tint: 0%;
        opacity: 1;
        text-opacity: 1;
        color: {theme.TEXT};
        border: none;
        border-top: solid {theme.INPUT_BORDER};
    }}
    """

    BINDINGS = [
        ("escape", "cancel_response", "Cancel response"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(
        self,
        session: Session | None = None,
        presenter: ConversationPresenter | None = None,
    ) -> None:
        super().__init__()
        self.session = session or Session.fake()
        self.presenter = presenter or ConversationPresenter()
        self._response_task: asyncio.Task[None] | None = None
        self._queued_prompts: deque[str] = deque()

    def compose(self) -> ComposeResult:
        yield ConversationView(id="conversation")
        yield StatusBar("idle", id="status")
        yield PromptInput(id="prompt")

    def on_mount(self) -> None:
        self._render()
        self.query_one(PromptInput).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return

        event.input.value = ""
        self.start_prompt(prompt)

    def start_prompt(self, prompt: str) -> None:
        if self._response_task is not None and not self._response_task.done():
            self._queued_prompts.append(prompt)
            return

        self._response_task = asyncio.create_task(self._run_prompt(prompt))

    async def _run_prompt(self, prompt: str) -> None:
        was_cancelled = False
        try:
            await self.submit_prompt(prompt)
        except asyncio.CancelledError:
            was_cancelled = True
            self.presenter.cancel_active_response()
            self._render()
        finally:
            self._response_task = None
            if not was_cancelled:
                self._start_next_queued_prompt()

    def action_cancel_response(self) -> None:
        if self._response_task is None or self._response_task.done():
            return

        self._queued_prompts.clear()
        self._response_task.cancel()
        self.presenter.cancel_active_response()
        self._render()

    def _start_next_queued_prompt(self) -> None:
        if self._queued_prompts:
            self.start_prompt(self._queued_prompts.popleft())

    async def submit_prompt(self, prompt: str) -> None:
        prompt_input = self.query_one(PromptInput)

        try:
            async for event in self.session.submit_user_message(prompt):
                self.presenter.apply(event)
                self._render()
        finally:
            prompt_input.focus()
            self._render()

    def _render(self) -> None:
        self.query_one(ConversationView).render_items(self.presenter.items)
        self.query_one(StatusBar).render_status(self.presenter.status)
