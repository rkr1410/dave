"""Fake provider client for tests and smoke runs."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from copy import deepcopy

from dave.core.requests import ChatRequest
from dave.core.stream_events import TextDelta
from dave.providers.client import ProviderClient, ProviderError


class FakeProviderClient(ProviderClient):
    def __init__(
        self,
        chunks: Iterable[str] = ("fake response",),
        fail_after_chunks: int | None = None,
        failure_message: str = "Fake provider failure",
    ) -> None:
        if fail_after_chunks is not None and fail_after_chunks < 0:
            raise ValueError("fail_after_chunks must be >= 0")

        self.chunks = tuple(chunks)
        self.fail_after_chunks = fail_after_chunks
        self.failure_message = failure_message
        self._requests: list[ChatRequest] = []

    @property
    def requests(self) -> tuple[ChatRequest, ...]:
        return tuple(deepcopy(request) for request in self._requests)

    async def stream(self, request: ChatRequest) -> AsyncIterator[TextDelta]:
        self._requests.append(deepcopy(request))

        yielded = 0
        for chunk in self.chunks:
            if self.fail_after_chunks is not None and yielded >= self.fail_after_chunks:
                raise ProviderError(self.failure_message)
            yielded += 1
            yield TextDelta(chunk)

        if self.fail_after_chunks is not None and yielded >= self.fail_after_chunks:
            raise ProviderError(self.failure_message)
