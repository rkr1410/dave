# DOMAIN

This is the domain model spike for Dave.

The goal is to name the first concepts and boundaries before runtime
implementation starts. It should stay small and only cover decisions needed for
the first headless MVP.

## Non-goals for this spike

- No storage design.
- No plugin API.
- No tool execution model. The *shape* of the tool loop is sketched below so
  later epics don't break the request lifecycle, but execution itself is out of
  scope.
- No workflow graph.
- No UI layout decisions.
- No provider-specific SDK modeling.

## Core boundary

Dave has three related but separate streams of information:

- Canonical events describe durable semantic session state changes.
- Stream events describe live execution progress.
- Trace records and artifacts describe raw/debug evidence.

Examples:

- `UserMessageAppended`, `RequestApproved`, and `AssistantMessageAppended` are
  canonical events.
- `RequestBuilt`, `RequestSent`, `TextDelta`, `ReasoningDelta`, and
  `ModelResponseFinished` are stream events.
- Raw SDK payloads, raw chunks, serialized requests, serialized responses, and
  large tool outputs belong in trace/artifact storage.

`TextDelta` does not need to be replayable. Replay should be able to rebuild the
conversation from semantic events such as `AssistantMessageAppended`.

## Core types

`Session`

The runtime boundary for an interactive conversation. It receives user input,
builds requests, sends requests, emits stream events, and appends canonical
events.

A session is the minimal runtime unit. Anything that needs its own context,
its own request lifecycle, and its own event log — a subagent included — is a
new session, not a structure inside an existing one. Parent/child relations
between sessions are recorded as events, not as object nesting.

`Turn` (derived concept, not a type)

The span from a `UserMessageAppended` to the assistant response that ends the
tool loop. Turns matter for UI grouping, compaction boundaries, branch points,
and cost accounting — but a turn is a view derived from the event log. There is
no `Turn` runtime object and none should be introduced.

`Branch`

A pointer into a conversation history. Branching is not part of the first MVP,
but the domain model should avoid assuming that a session has only one linear
future.

`Event`

A durable semantic state change. Events are the source of truth for replay and
message materialization.

Every event has its own `id` and a `parent_id` pointing at the event it follows.
A linear session is just the degenerate case where every event has one child.
This costs nothing now and makes branching a pointer operation later instead of
a data migration.

Initial canonical events:

- `UserMessageAppended`
- `RequestApproved`
- `RequestRejected`
- `AssistantMessageAppended`
- `ToolResultAppended` (shape only; execution is out of scope)
- `ModelResponseFailed`

`Message`

A materialized view used to build model requests and display conversation state.
Messages are derived from canonical events; they are not the source of truth.

`ChatRequest`

Dave's provider-neutral request object. It is the object used by the runtime and
debug visibility; debug views must not reconstruct requests from SDK internals.

`StreamEvent`

A live execution signal emitted by the runtime for UI, CLI, and debug consumers.
Stream events are not necessarily durable or replayable.

Initial stream events:

- `RequestBuilt`
- `RequestSent`
- `TextDelta`
- `ReasoningDelta`
- `ModelResponseFinished`

`ModelResponseFinished` marks the end of a single model response, not the end
of a turn. In the tool loop one turn contains several model responses, so
several `ModelResponseFinished` events.

`ToolCall`

A provider-neutral description of a requested tool call. The execution model is
out of scope for this spike.

`ArtifactRef`

A stable reference to data stored outside the canonical event payload. Use it for
raw requests, raw responses, raw chunks, and large tool outputs.

## Request lifecycle

`build_request()` and `send_request()` should be separate operations from the
start.

`build_request()` creates a candidate `ChatRequest` from materialized messages
and emits `RequestBuilt`.

The inspect/edit boundary happens after `RequestBuilt` and before
`RequestApproved`. This boundary may be automatic at first, but it must remain a
real boundary so a future UI, user, or plugin can approve, reject, or edit the
request before it is sent.

`RequestApproved` is the canonical event that records the approved request. It
is the right replay point for "what request was allowed to be sent".

The approved request payload is the whole conversation, so it belongs in
artifact storage per the invariants below. `RequestApproved` carries an
`ArtifactRef` to the serialized request plus small metadata (model, message
count), not the payload itself.

`RequestRejected` is the canonical event for the other outcome of the boundary.
`ModelResponseFailed` records a send or stream failure, so replay can explain why an
approved request has no assistant message. A stream aborted mid-response must
not produce a partial `AssistantMessageAppended`. The evidence is not lost:
`ModelResponseFailed` carries `ArtifactRef`s to the error details and to whatever
partial stream output exists in trace storage, so failed responses stay
inspectable.

`send_request()` sends the approved request. It should not rebuild the request.

## Happy path

```text
submit_user_message()
  -> append UserMessageAppended canonical event
  -> materialize_messages()
  -> build_request()
  -> emit RequestBuilt StreamEvent
  -> optional inspect/edit boundary
  -> append RequestApproved canonical event
  -> send_request(approved_request)
  -> emit RequestSent StreamEvent
  -> stream TextDelta/ReasoningDelta StreamEvents
  -> accumulate assistant draft
  -> emit ModelResponseFinished StreamEvent
  -> append AssistantMessageAppended canonical event
```

`ModelResponseFinished` reports the stream ending; the canonical commit
follows it. The canonical event is the signal that the message is durable,
so it comes last in the iteration.

## Tool loop shape (sketch)

Not part of the first MVP. This exists so the happy path above is understood as
a special case of the general turn, and so the UI epic doesn't bake in the
assumption that every request follows a user message.

A turn is a loop, not a line:

```text
submit_user_message()
  -> append UserMessageAppended
  -> loop:
       materialize_messages()
       ...
       (out of scope here):
           if the assistant message contains no tool calls: break
           execute tools
       ...
       append ToolResultAppended for each result
```

Consequences the MVP must not contradict:

- `AssistantMessageAppended` can contain tool calls (`ToolCall` values), not
  just text.
- `build_request()` runs once per loop iteration, so `RequestApproved` and the
  inspect/edit boundary happen per iteration — not once per user message.
- `ToolResultAppended` is a canonical event; large tool outputs go to artifact
  storage via `ArtifactRef`.

## Package sketch

The package layout should make the event boundary obvious:

```text
dave/
  core/
    session.py
    events.py
    stream_events.py
    messages.py
    tool_calls.py
    requests.py
    branches.py
    artifacts.py
  providers/
    client.py
    stream_adapter.py
```

`providers/` holds everything provider-specific: translating `ChatRequest` to a
concrete SDK and translating provider chunks to neutral `StreamEvent`s. Nothing
outside `providers/` may import a provider SDK. The name is deliberately not
`model/` (overloaded with "domain model" and "which LLM") and not `transport/`
(this layer adapts semantics, not just wires).

Example imports:

```python
from dave.core.events import (
    AssistantMessageAppended,
    RequestApproved,
    RequestRejected,
    ModelResponseFailed,
    ToolResultAppended,
    UserMessageAppended,
)
from dave.core.stream_events import (
    ReasoningDelta,
    RequestBuilt,
    RequestSent,
    ModelResponseFinished,
    TextDelta,
)
from dave.core.requests import ChatRequest
```

## Invariants

- The canonical event log stores semantic session events.
- Trace/artifact storage stores raw evidence and large payloads.
- An `ArtifactRef` used by a canonical event points to an immutable artifact.
  Replay from canonical events must never depend on mutable external state.
- `messages[]` is always a materialized view.
- Debug visibility is built from the same request/response objects used by the
  runtime.
- Every important decision should be inspectable and overridable.
