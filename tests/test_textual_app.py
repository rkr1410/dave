from __future__ import annotations

import asyncio
import unittest
from collections.abc import AsyncIterator

from dave.runtime.events import AssistantMessageAppended
from dave.runtime.requests import ModelRequest
from dave.runtime.session import Session
from dave.runtime.stream_events import TextDelta
from dave.ui.textual.app import DaveTextualApp
from dave.ui.textual.widgets import ConversationView, PromptInput


class HangingProvider:
    def __init__(self) -> None:
        self.waiting = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def stream(self, request: ModelRequest) -> AsyncIterator[TextDelta]:
        yield TextDelta("partial")
        self.waiting.set()

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


class TextualAppTest(unittest.IsolatedAsyncioTestCase):
    async def test_conversation_view_scrolls_long_output(self) -> None:
        long_output = "\n".join(f"line {line_number}" for line_number in range(40))
        app = DaveTextualApp(session=Session.fake(chunks=(long_output,)))

        async with app.run_test(size=(60, 10)) as pilot:
            await app.submit_prompt("hello")
            await pilot.pause()

            conversation = app.query_one(ConversationView)

            self.assertGreater(conversation.max_scroll_y, 0)
            self.assertEqual(conversation.scroll_y, conversation.max_scroll_y)

    async def test_escape_cancels_in_flight_response(self) -> None:
        provider = HangingProvider()
        session = Session(model="test-model", provider=provider)
        app = DaveTextualApp(session=session)

        async with app.run_test(size=(60, 10)) as pilot:
            app.start_prompt("hello")
            await provider.waiting.wait()

            await pilot.press("escape")
            await provider.cancelled.wait()
            await pilot.pause()

            prompt_input = app.query_one(PromptInput)

            self.assertEqual(
                [(item.role, item.text, item.state) for item in app.presenter.items],
                [
                    ("user", "hello", "done"),
                    ("assistant", "partial", "cancelled"),
                ],
            )
            self.assertEqual(app.presenter.status, "cancelled")
            self.assertFalse(prompt_input.disabled)
            self.assertFalse(
                any(
                    isinstance(event, AssistantMessageAppended)
                    for event in session.events
                )
            )


if __name__ == "__main__":
    unittest.main()
