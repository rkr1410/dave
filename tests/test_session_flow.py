import unittest

from dave.core.artifacts import InMemoryArtifactStore
from dave.core.events import (
    AssistantMessageAppended,
    ModelResponseFailed,
    RequestApproved,
    RequestRejected,
    SystemPromptSet,
    UserMessageAppended,
)
from dave.core.messages import (
    AssistantMessage,
    SystemMessage,
    UserMessage,
    materialize_messages,
)
from dave.core.requests import Approve, ModelRequest, Reject
from dave.core.session import Session, SessionEvent
from dave.core.stream_events import (
    ModelResponseFinished,
    RequestBuilt,
    RequestSent,
    TextDelta,
)
from dave.providers.fake import FakeProviderClient


async def collect_events(session: Session) -> list[SessionEvent]:
    events: list[SessionEvent] = []
    async for event in session.submit_user_message("hello"):
        events.append(event)
    return events


class SessionFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_happy_path_streams_and_materializes_conversation(self) -> None:
        artifact_store = InMemoryArtifactStore()
        provider = FakeProviderClient(("hello", " world"))
        session = Session(
            model="fake-model",
            provider=provider,
            artifact_store=artifact_store,
        )
        system_event = session.set_system_prompt("You are concise.")

        events = await collect_events(session)

        self.assertIsInstance(system_event, SystemPromptSet)
        self.assertEqual(
            [type(event) for event in events],
            [
                UserMessageAppended,
                RequestBuilt,
                RequestApproved,
                RequestSent,
                TextDelta,
                TextDelta,
                ModelResponseFinished,
                AssistantMessageAppended,
            ],
        )

        self.assertIsInstance(events[1], RequestBuilt)
        self.assertIsInstance(events[2], RequestApproved)
        self.assertIsInstance(events[3], RequestSent)
        built_request = events[1].request
        approved_event = events[2]
        sent_request = events[3].request

        self.assertEqual(
            built_request,
            ModelRequest(
                model="fake-model",
                messages=(
                    SystemMessage(content="You are concise."),
                    UserMessage(content="hello"),
                ),
            ),
        )
        self.assertEqual(artifact_store.get(approved_event.request_ref), sent_request)
        self.assertEqual(provider.requests, (sent_request,))
        self.assertEqual(approved_event.message_count, 2)
        self.assertEqual(
            [type(event) for event in session.events],
            [
                SystemPromptSet,
                UserMessageAppended,
                RequestApproved,
                AssistantMessageAppended,
            ],
        )
        self.assertEqual(
            materialize_messages(session.events),
            (
                SystemMessage(content="You are concise."),
                UserMessage(content="hello"),
                AssistantMessage(content="hello world"),
            ),
        )

    async def test_approval_boundary_can_edit_or_reject_request(self) -> None:
        edited_request = ModelRequest(
            model="edited-model",
            messages=(UserMessage(content="edited"),),
        )

        async def edit_request(request: ModelRequest) -> Approve:
            return Approve(edited_request)

        edit_store = InMemoryArtifactStore()
        edit_provider = FakeProviderClient(("ok",))
        edit_session = Session(
            provider=edit_provider,
            artifact_store=edit_store,
            approver=edit_request,
        )

        edit_events = await collect_events(edit_session)

        self.assertIsInstance(edit_events[2], RequestApproved)
        self.assertIsInstance(edit_events[3], RequestSent)
        self.assertEqual(edit_events[3].request, edited_request)
        self.assertEqual(edit_provider.requests, (edited_request,))
        self.assertEqual(edit_store.get(edit_events[2].request_ref), edited_request)

        async def reject_request(request: ModelRequest) -> Reject:
            return Reject("no")

        reject_provider = FakeProviderClient(("should not stream",))
        reject_session = Session(provider=reject_provider, approver=reject_request)

        reject_events = await collect_events(reject_session)

        self.assertEqual(
            [type(event) for event in reject_events],
            [UserMessageAppended, RequestBuilt, RequestRejected],
        )
        self.assertIsInstance(reject_events[2], RequestRejected)
        self.assertEqual(reject_events[2].reason, "no")
        self.assertEqual(reject_provider.requests, ())
        self.assertEqual(
            [type(event) for event in reject_session.events],
            [UserMessageAppended, RequestRejected],
        )

    async def test_provider_failure_commits_failure_without_partial_message(self) -> None:
        before_text_store = InMemoryArtifactStore()
        before_text_provider = FakeProviderClient(
            ("never",),
            fail_after_chunks=0,
            failure_message="boom before text",
        )
        before_text_session = Session(
            provider=before_text_provider,
            artifact_store=before_text_store,
        )

        before_text_events = await collect_events(before_text_session)

        self.assertEqual(
            [type(event) for event in before_text_events],
            [
                UserMessageAppended,
                RequestBuilt,
                RequestApproved,
                RequestSent,
                ModelResponseFailed,
            ],
        )
        before_text_failure = before_text_events[-1]
        self.assertIsInstance(before_text_failure, ModelResponseFailed)
        self.assertEqual(
            before_text_store.get(before_text_failure.error_ref),
            {"type": "ProviderError", "message": "boom before text"},
        )
        self.assertIsNone(before_text_failure.partial_output_ref)
        self.assertEqual(
            materialize_messages(before_text_session.events),
            (UserMessage(content="hello"),),
        )

        artifact_store = InMemoryArtifactStore()
        provider = FakeProviderClient(
            ("part", "ial"),
            fail_after_chunks=1,
            failure_message="boom",
        )
        session = Session(provider=provider, artifact_store=artifact_store)

        events = await collect_events(session)

        self.assertEqual(
            [type(event) for event in events],
            [
                UserMessageAppended,
                RequestBuilt,
                RequestApproved,
                RequestSent,
                TextDelta,
                ModelResponseFailed,
            ],
        )
        self.assertFalse(
            any(isinstance(event, ModelResponseFinished) for event in events)
        )
        self.assertFalse(
            any(isinstance(event, AssistantMessageAppended) for event in events)
        )

        failure = events[-1]
        self.assertIsInstance(failure, ModelResponseFailed)
        self.assertEqual(
            artifact_store.get(failure.error_ref),
            {"type": "ProviderError", "message": "boom"},
        )
        self.assertEqual(artifact_store.get(failure.partial_output_ref), "part")
        self.assertEqual(
            materialize_messages(session.events),
            (UserMessage(content="hello"),),
        )


if __name__ == "__main__":
    unittest.main()
