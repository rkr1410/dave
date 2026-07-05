"""Headless session runtime."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from copy import deepcopy

from dave.runtime.artifacts import InMemoryArtifactStore
from dave.runtime.event_log import EventLog
from dave.runtime.events import (
    AssistantMessageAppended,
    Event,
    ModelResponseFailed,
    RequestApproved,
    RequestRejected,
    SystemPromptSet,
    UserMessageAppended,
)
from dave.runtime.messages import materialize_messages
from dave.runtime.requests import Approve, ModelRequest, Reject
from dave.runtime.stream_events import (
    ModelResponseFinished,
    RequestBuilt,
    RequestSent,
    StreamEvent,
    TextDelta,
)
from dave.providers.client import ProviderClient, ProviderError
from dave.providers.fake import FakeProviderClient

Approver = Callable[[ModelRequest], Awaitable[Approve | Reject]]
SessionEvent = Event | StreamEvent


async def auto_approve(request: ModelRequest) -> Approve:
    return Approve(request)


class Session:
    def __init__(
        self,
        model: str,
        provider: ProviderClient,
        event_log: EventLog | None = None,
        artifact_store: InMemoryArtifactStore | None = None,
        approver: Approver | None = None,
    ) -> None:
        self.model = model
        self.provider = provider
        self._event_log = event_log or EventLog()
        self._artifact_store = artifact_store or InMemoryArtifactStore()
        self.approver = approver or auto_approve

    @classmethod
    def fake(
        cls,
        model: str = "fake",
        chunks: tuple[str, ...] = ("fake response",),
        event_log: EventLog | None = None,
        artifact_store: InMemoryArtifactStore | None = None,
        approver: Approver | None = None,
    ) -> Session:
        return cls(
            model=model,
            provider=FakeProviderClient(chunks),
            event_log=event_log,
            artifact_store=artifact_store,
            approver=approver,
        )

    @property
    def events(self) -> tuple[Event, ...]:
        return self._event_log.events

    def set_system_prompt(self, content: str) -> SystemPromptSet:
        return self._event_log.append(SystemPromptSet(content))

    def build_request(self) -> ModelRequest:
        return ModelRequest(
            model=self.model,
            messages=materialize_messages(self._event_log.events),
        )

    def send_request(self, request: ModelRequest) -> AsyncIterator[StreamEvent]:
        return self.provider.stream(request)

    async def submit_user_message(self, text: str) -> AsyncIterator[SessionEvent]:
        user_event = self._event_log.append(UserMessageAppended(text))
        yield user_event

        request = self.build_request()
        yield RequestBuilt(deepcopy(request))

        approval = await self.approver(request)
        if isinstance(approval, Reject):
            rejected_event = self._event_log.append(RequestRejected(approval.reason))
            yield rejected_event
            return

        approved_request = deepcopy(approval.request)
        request_ref = self._artifact_store.put(approved_request, "requests")
        approved_event = self._event_log.append(
            RequestApproved(
                request_ref=request_ref,
                model=approved_request.model,
                message_count=len(approved_request.messages),
            )
        )
        yield approved_event

        yield RequestSent(deepcopy(approved_request))

        assistant_text = ""
        try:
            async for event in self.send_request(approved_request):
                if isinstance(event, TextDelta):
                    assistant_text += event.text
                yield event
        except ProviderError as error:
            error_ref = self._artifact_store.put(
                {
                    "type": type(error).__name__,
                    "message": str(error),
                },
                "errors",
            )
            partial_output_ref = (
                self._artifact_store.put(assistant_text, "partial-outputs")
                if assistant_text
                else None
            )
            failed_event = self._event_log.append(
                ModelResponseFailed(
                    error_ref=error_ref,
                    partial_output_ref=partial_output_ref,
                )
            )
            yield failed_event
            return

        yield ModelResponseFinished()

        assistant_event = self._event_log.append(
            AssistantMessageAppended(assistant_text)
        )
        yield assistant_event
