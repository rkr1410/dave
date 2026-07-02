"""Provider client protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from dave.core.requests import ChatRequest
from dave.core.stream_events import StreamEvent


class ProviderError(RuntimeError):
    pass


class ProviderClient(Protocol):
    def stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        pass
