import unittest

from dave.runtime.events import AssistantMessageAppended, UserMessageAppended
from dave.runtime.stream_events import (
    ModelResponseFinished,
    ReasoningDelta,
    TextDelta,
)
from dave.ui.textual.presenter import ConversationPresenter


class ConversationPresenterTest(unittest.TestCase):
    def test_maps_streaming_events_to_transcript_items(self) -> None:
        presenter = ConversationPresenter()

        presenter.apply(UserMessageAppended("hello"))
        presenter.apply(ReasoningDelta("thinking"))
        presenter.apply(TextDelta("hi"))
        presenter.apply(ModelResponseFinished())
        presenter.apply(AssistantMessageAppended("hi there"))

        self.assertEqual(
            [(item.role, item.text, item.state) for item in presenter.items],
            [
                ("user", "hello", "done"),
                ("reasoning", "thinking", "done"),
                ("assistant", "hi there", "done"),
            ],
        )
        self.assertEqual(presenter.status, "idle")

    def test_cancel_keeps_user_message_and_marks_active_output(self) -> None:
        presenter = ConversationPresenter()

        presenter.apply(UserMessageAppended("abc"))
        presenter.apply(ReasoningDelta("thinking"))
        presenter.apply(TextDelta("partial"))
        presenter.cancel_active_response()

        self.assertEqual(
            [(item.role, item.text, item.state) for item in presenter.items],
            [
                ("user", "abc", "done"),
                ("reasoning", "thinking", "cancelled"),
                ("assistant", "partial", "cancelled"),
            ],
        )
        self.assertEqual(presenter.status, "cancelled")
