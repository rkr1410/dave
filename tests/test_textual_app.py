from __future__ import annotations

import asyncio
import unittest
from collections.abc import AsyncIterator

from dave.runtime.events import AssistantMessageAppended
from dave.runtime.requests import ModelRequest
from dave.runtime.session import Session
from dave.runtime.stream_events import TextDelta
from dave.ui.textual.app import DaveTextualApp
from dave.ui.textual.presenter import TranscriptItem
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


class QueuedProvider:
    def __init__(self) -> None:
        self.first_waiting = asyncio.Event()
        self.release_first = asyncio.Event()
        self.second_seen = asyncio.Event()
        self.prompts: list[str] = []

    async def stream(self, request: ModelRequest) -> AsyncIterator[TextDelta]:
        self.prompts.append(request.messages[-1].content)

        if len(self.prompts) == 1:
            yield TextDelta("first")
            self.first_waiting.set()
            await self.release_first.wait()
            return

        yield TextDelta("second")
        self.second_seen.set()


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

    async def test_conversation_view_keeps_manual_scroll_position(self) -> None:
        initial_output = "\n".join(f"line {line_number}" for line_number in range(40))
        updated_output = initial_output + "\n" + "\n".join(
            f"extra {line_number}" for line_number in range(20)
        )
        app = DaveTextualApp(session=Session.fake())

        async with app.run_test(size=(60, 10)) as pilot:
            conversation = app.query_one(ConversationView)
            conversation.render_items((TranscriptItem("assistant", initial_output),))
            await pilot.pause()

            self.assertGreater(conversation.max_scroll_y, 0)

            conversation.scroll_to(y=0, animate=False, immediate=True)
            await pilot.pause()

            conversation.render_items((TranscriptItem("assistant", updated_output),))
            await pilot.pause()

            self.assertEqual(conversation.scroll_y, 0)

    async def test_conversation_view_collapses_reasoning_by_default(self) -> None:
        app = DaveTextualApp(session=Session.fake())

        async with app.run_test(size=(60, 10)) as pilot:
            conversation = app.query_one(ConversationView)
            items = (TranscriptItem("reasoning", "hidden reasoning", "streaming"),)

            conversation.render_items(items)
            await pilot.pause()

            self.assertIn(0, conversation._collapsed_reasoning_indices)

            conversation._collapsed_reasoning_indices.remove(0)
            conversation._manually_expanded_reasoning_indices.add(0)
            conversation.render_items(items)
            await pilot.pause()

            self.assertNotIn(0, conversation._collapsed_reasoning_indices)

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

    async def test_prompt_queues_while_response_streams(self) -> None:
        provider = QueuedProvider()
        session = Session(model="test-model", provider=provider)
        app = DaveTextualApp(session=session)

        async with app.run_test(size=(60, 10)) as pilot:
            app.start_prompt("first")
            await provider.first_waiting.wait()

            prompt_input = app.query_one(PromptInput)
            self.assertFalse(prompt_input.disabled)

            prompt_input.value = "second"
            await pilot.press("enter")
            await pilot.pause()

            self.assertEqual(prompt_input.value, "")
            self.assertEqual(provider.prompts, ["first"])

            provider.release_first.set()
            await provider.second_seen.wait()
            await pilot.pause()

            self.assertEqual(provider.prompts, ["first", "second"])


if __name__ == "__main__":
    unittest.main()
