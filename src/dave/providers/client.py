"""Provider client protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from dave.runtime.requests import ModelRequest
from dave.runtime.stream_events import StreamEvent


class ProviderError(RuntimeError):
    pass


class ProviderClient(Protocol):
    def stream(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        pass
