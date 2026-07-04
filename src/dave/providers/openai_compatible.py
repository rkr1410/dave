"""OpenAI-compatible provider client."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Iterable
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionChunk,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

from dave.core.messages import (
    AssistantMessage,
    DeveloperMessage,
    Message,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from dave.core.requests import ChatRequest
from dave.core.stream_events import ReasoningDelta, StreamEvent, TextDelta
from dave.providers.client import ProviderClient, ProviderError

DEFAULT_API_KEY = "dummy"


class OpenAICompatibleProviderClient(ProviderClient):
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")

        self.base_url = base_url
        self.api_key = api_key or DEFAULT_API_KEY
        self._client = client or AsyncOpenAI(
            base_url=base_url,
            api_key=self.api_key,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        try:
            stream = ensure_async_iterable_stream(
                await self._client.chat.completions.create(
                    model=request.model,
                    messages=serialize_messages_for_openai(request.messages),
                    stream=True,
                )
            )

            async for event in adapt_openai_chat_completion_chunks(stream):
                yield event
        except ProviderError:
            raise
        except Exception as error:
            raise ProviderError(format_provider_error(error)) from error


def serialize_messages_for_openai(
    messages: Iterable[Message],
) -> list[ChatCompletionMessageParam]:
    return [serialize_message_for_openai(message) for message in messages]


def serialize_message_for_openai(message: Message) -> ChatCompletionMessageParam:
    match message:
        case SystemMessage():
            return to_openai_system_message_param(message)
        case DeveloperMessage():
            return to_openai_developer_message_param(message)
        case UserMessage():
            return to_openai_user_message_param(message)
        case AssistantMessage():
            return to_openai_assistant_message_param(message)
        case ToolMessage():
            return to_openai_tool_message_param(message)


def ensure_async_iterable_stream(stream: Any) -> AsyncIterable[ChatCompletionChunk]:
    if not hasattr(stream, "__aiter__"):
        raise ProviderError("Expected streaming response")
    return stream


def to_openai_system_message_param(
    message: SystemMessage,
) -> ChatCompletionSystemMessageParam:
    return ChatCompletionSystemMessageParam(
        role="system",
        content=message.content,
    )


def to_openai_developer_message_param(
    message: DeveloperMessage,
) -> ChatCompletionDeveloperMessageParam:
    return ChatCompletionDeveloperMessageParam(
        role="developer",
        content=message.content,
    )


def to_openai_user_message_param(
    message: UserMessage,
) -> ChatCompletionUserMessageParam:
    return ChatCompletionUserMessageParam(
        role="user",
        content=message.content,
    )


def to_openai_assistant_message_param(
    message: AssistantMessage,
) -> ChatCompletionAssistantMessageParam:
    if message.tool_calls:
        raise ProviderError("Tool calls are not supported yet")
    return ChatCompletionAssistantMessageParam(
        role="assistant",
        content=message.content,
    )


def to_openai_tool_message_param(
    message: ToolMessage,
) -> ChatCompletionToolMessageParam:
    return ChatCompletionToolMessageParam(
        role="tool",
        content=message.content,
        tool_call_id=message.tool_call_id,
    )


async def adapt_openai_chat_completion_chunks(
    chunks: AsyncIterable[ChatCompletionChunk],
) -> AsyncIterator[StreamEvent]:
    async for chunk in chunks:
        for choice in chunk.choices:
            delta = choice.delta
            if delta is None:
                continue

            if delta.tool_calls or delta.function_call:
                raise ProviderError("Tool calls are not supported yet")

            reasoning = get_reasoning_content(delta)
            if reasoning:
                yield ReasoningDelta(str(reasoning))

            if delta.content:
                yield TextDelta(delta.content)


def get_reasoning_content(delta: Any) -> Any:
    reasoning = getattr(delta, "reasoning_content", None)
    if reasoning is None:
        return getattr(delta, "reasoning", None)
    return reasoning


def format_provider_error(error: Exception) -> str:
    message = str(error)
    if message:
        return f"{type(error).__name__}: {message}"
    return type(error).__name__
