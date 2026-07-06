"""Textual app skeleton for Dave."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Input

from dave.runtime.session import Session
from dave.ui.textual.presenter import ConversationPresenter
from dave.ui.textual.widgets import ConversationView, PromptInput, StatusBar


class DaveTextualApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    ConversationView {
        height: 1fr;
        min-height: 0;
        padding: 1;
        border: solid $surface;
        overflow-x: hidden;
        overflow-y: scroll;
    }

    StatusBar {
        height: 1;
    }

    PromptInput {
        height: 3;
    }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(
        self,
        session: Session | None = None,
        presenter: ConversationPresenter | None = None,
    ) -> None:
        super().__init__()
        self.session = session or Session.fake()
        self.presenter = presenter or ConversationPresenter()

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
        await self.submit_prompt(prompt)

    async def submit_prompt(self, prompt: str) -> None:
        prompt_input = self.query_one(PromptInput)
        prompt_input.disabled = True

        try:
            async for event in self.session.submit_user_message(prompt):
                self.presenter.apply(event)
                self._render()
        finally:
            prompt_input.disabled = False
            prompt_input.focus()
            self._render()

    def _render(self) -> None:
        self.query_one(ConversationView).render_items(self.presenter.items)
        self.query_one(StatusBar).render_status(self.presenter.status)
