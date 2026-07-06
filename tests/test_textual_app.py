from __future__ import annotations

import unittest

from dave.runtime.session import Session
from dave.ui.textual.app import DaveTextualApp
from dave.ui.textual.widgets import ConversationView


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


if __name__ == "__main__":
    unittest.main()
