import unittest

from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import (
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
)

from dave.core.messages import UserMessage
from dave.core.requests import ModelRequest
from dave.core.stream_events import ReasoningDelta, TextDelta
from dave.providers.client import ProviderError
from dave.providers.openai_compatible import (
    OpenAICompatibleProviderClient,
    adapt_openai_chat_completion_chunks,
)


class AsyncChunks:
    def __init__(self, chunks):
        self._chunks = tuple(chunks)

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for chunk in self._chunks:
            yield chunk


class FakeCompletions:
    def __init__(self, chunks=(), error=None):
        self.chunks = chunks
        self.error = error

    async def create(self, **kwargs):
        if self.error is not None:
            raise self.error
        return AsyncChunks(self.chunks)


class FakeChat:
    def __init__(self, completions):
        self.completions = completions


class FakeOpenAIClient:
    def __init__(self, completions):
        self.chat = FakeChat(completions)


def completion_chunk(
    delta: ChoiceDelta | None = None,
    *,
    finish_reason=None,
) -> ChatCompletionChunk:
    return ChatCompletionChunk(
        id="chunk-1",
        choices=[
            Choice(
                delta=delta or ChoiceDelta(),
                finish_reason=finish_reason,
                index=0,
            )
        ],
        created=0,
        model="test-model",
        object="chat.completion.chunk",
    )


def empty_completion_chunk() -> ChatCompletionChunk:
    return ChatCompletionChunk(
        id="chunk-1",
        choices=[],
        created=0,
        model="test-model",
        object="chat.completion.chunk",
    )


class OpenAICompatibleProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_adapts_reasoning_and_text_chunks(self) -> None:
        chunks = AsyncChunks(
            [
                completion_chunk(ChoiceDelta(role="assistant")),
                completion_chunk(ChoiceDelta(reasoning_content="think")),
                completion_chunk(ChoiceDelta(reasoning=" more")),
                completion_chunk(ChoiceDelta(content="answer")),
                completion_chunk(finish_reason="stop"),
                empty_completion_chunk(),
            ]
        )

        events = [
            event async for event in adapt_openai_chat_completion_chunks(chunks)
        ]

        self.assertEqual(
            events,
            [
                ReasoningDelta("think"),
                ReasoningDelta(" more"),
                TextDelta("answer"),
            ],
        )

    async def test_rejects_streamed_tool_calls(self) -> None:
        chunks = AsyncChunks(
            [
                completion_chunk(
                    ChoiceDelta(
                        tool_calls=[
                            ChoiceDeltaToolCall(
                                index=0,
                                id="call-1",
                                type="function",
                            ),
                        ],
                    )
                ),
            ]
        )

        with self.assertRaisesRegex(ProviderError, "Tool calls are not supported"):
            async for _ in adapt_openai_chat_completion_chunks(chunks):
                pass

    async def test_provider_maps_sdk_errors_to_provider_error(self) -> None:
        completions = FakeCompletions(error=RuntimeError("boom"))
        provider = OpenAICompatibleProviderClient(
            base_url="http://test/v1",
            client=FakeOpenAIClient(completions),
        )

        with self.assertRaisesRegex(ProviderError, "RuntimeError: boom"):
            async for _ in provider.stream(
                ModelRequest(
                    model="test-model",
                    messages=(UserMessage(content="hello"),),
                )
            ):
                pass


if __name__ == "__main__":
    unittest.main()
