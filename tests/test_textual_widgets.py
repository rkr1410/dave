from __future__ import annotations

import unittest

from dave.ui.textual import theme
from dave.ui.textual.presenter import TranscriptItem
from dave.ui.textual.widgets import TOGGLE_REASONING_META, format_item, format_status


class TextualWidgetsTest(unittest.TestCase):
    def test_formats_transcript_item_text(self) -> None:
        rendered = format_item(TranscriptItem("assistant", "hello", "cancelled"))

        self.assertEqual(rendered.plain, "dave: hello [cancelled]")

    def test_formats_status_text(self) -> None:
        rendered = format_status("streaming")

        self.assertEqual(rendered.plain, "status: streaming")

    def test_formats_collapsible_reasoning(self) -> None:
        expanded = format_item(
            TranscriptItem("reasoning", "hidden reasoning"),
            index=2,
        )
        collapsed = format_item(
            TranscriptItem("reasoning", "hidden reasoning"),
            index=2,
            collapsed=True,
        )

        self.assertEqual(expanded.plain, "thinking[-]: hidden reasoning")
        self.assertEqual(collapsed.plain, "thinking[+]: [collapsed]")
        self.assertEqual(expanded.spans[1].style.meta[TOGGLE_REASONING_META], 2)

    def test_formats_streaming_reasoning_pulse(self) -> None:
        rendered = format_item(
            TranscriptItem("reasoning", "hidden reasoning", "streaming"),
            pulse_phase=1,
        )

        self.assertEqual(rendered.plain, "thinking[-]: hidden reasoning [streaming]")
        self.assertEqual(rendered.spans[0].style, theme.REASONING_LABEL_PULSE_STYLES[1])


if __name__ == "__main__":
    unittest.main()
