# TODO

## Epic 1: Core session runtime

Goal: headless session runtime with fake model output, canonical events,
stream events, and a real request approval boundary. No real provider, no disk
storage, no UI, no tools.

Exit criterion:

```python
async for event in session.submit_user_message("hello"):
    ...
```

works headless, emits events in a sensible order, and leaves a canonical event
log from which the conversation can be materialized.

### Decisions to record in code

- The runtime is asyncio-native.
- `submit_user_message()` is an async generator yielding both stream events
  and canonical events, in order of occurrence. The canonical log stays the
  only source of truth; the generator is a live view and consumers filter by
  type.
- A provider failure ends the stream normally: the canonical
  `ModelResponseFailed` is yielded through the generator like any canonical
  event — there is no separate failure stream event. Exceptions are for bugs,
  not for domain-level failures.
- The approval boundary is an injectable approver (async callable
  `ChatRequest -> Approve(request) | Reject(reason)`), defaulting to
  auto-approve. Approve may carry an edited request. It is a seam, not an
  inline shortcut.

### Tasks

- [x] Create package skeleton from `DOMAIN.md` package sketch
  - include `dave/providers/fake.py` for tests and smoke runs
- [x] Define minimal domain dataclasses
  - canonical: `UserMessageAppended`, `RequestApproved`, `RequestRejected`,
    `AssistantMessageAppended`, `ToolResultAppended`, `ModelResponseFailed`
  - stream: `RequestBuilt`, `RequestSent`, `TextDelta`, `ReasoningDelta`,
    `ModelResponseFinished`
  - other: `Message`, `ChatRequest`, `ArtifactRef`, `ToolCall`, `Approve`,
    `Reject`
  - *dev comment* `ToolCall` lives in `core/tool_calls.py` so `messages.py` and `requests.py`
    do not depend on each other.
- [x] Add in-memory event log
  - append canonical events
  - assign ids, maintain `parent_id`
  - expose current event list
- [x] Add in-memory artifact store
  - store/retrieve payloads by `ArtifactRef`
  - can store a serialized request payload for `RequestApproved`
  - can store error details and partial output payloads for `ModelResponseFailed`
- [x] Add message materialization
  - build `messages[]` from canonical events
  - support user and assistant messages
  - ignore event types the materializer does not know (not just
    `RequestApproved`) so future canonical events don't break it
- [x] Add fake provider client
  - accepts `ChatRequest`
  - streams deterministic chunks
  - can simulate failure for tests
- [ ] Implement `Session.submit_user_message()` happy path
  - append `UserMessageAppended`
  - materialize messages
  - build `ChatRequest`, emit `RequestBuilt`
  - call the approver (default auto-approve), append `RequestApproved`
  - on reject: append `RequestRejected`, yield it, end the generator —
    nothing is sent
  - send, emit `RequestSent`
  - stream `TextDelta`, accumulate assistant draft
  - emit `ModelResponseFinished`
  - append and yield `AssistantMessageAppended` (last event of the
    iteration — the durable-commit signal consumers refresh on)
- [ ] Handle provider failure
  - append `ModelResponseFailed` with error/partial-output artifact refs
  - do not append a partial `AssistantMessageAppended`
  - yield `ModelResponseFailed` and end the generator normally
- [ ] Add tests
  - happy path event order
  - message materialization
  - request is built before sent
  - approved request is the sent request
  - an approver that edits the request → the edited request is sent
  - a rejecting approver → `RequestRejected` appended, nothing sent, no
    assistant message
  - failure does not append a partial assistant message
  - failure event carries refs that resolve in the artifact store
  - event ids / parent ids are chained
  - materializer ignores unknown event types
- [ ] Wire CLI smoke command (optional; skip if it bloats the slice)
  - minimal hidden command runs one fake session and prints events

Out of scope (later epics): real OpenAI-compatible client (epic 2), disk
storage (epic 5), UI (epic 6), tool execution (epic 7), interactive approval
UX (epic 1 only proves the seam works), branching.

## Epic 2 notes

- Decide whether provider-facing request/response/debug schemas should use
  Pydantic models instead of plain dataclasses.
- Decide JSON argument validation/serialization for `ToolCall.arguments` at the
  provider boundary; avoid ad hoc frozen-json machinery in core unless the
  boundary actually needs it.

## Open questions

- How much pluggability do we want? Allow user extensions to emit events
  that e.g. the artifact store should be aware of? How much is too much (e.g.
  if the core loses ful control of messages[] materialization, we lose debug/replay/compatibilty
  without the exact plugin versions)

## Soon after Epic 1

- If first real use shows that Dave needs a system/developer prompt and simple
  `list_files` / `read_file` tool calls to be useful, add a small spike for the
  cheapest coherent path: enough to work, without falling into the full tool
  registry/plugin implementation.

## Later

- Add optional install settings:
  - `DAVE_BIN_DIR`: directory for the global `dave` wrapper.
  - `DAVE_VENV_DIR`: virtualenv path.
  - `DAVE_INSTALL_ROOT`: directory for commit install snapshots.
  - `PYTHON_BIN`: Python executable used to create the venv.
  - `DAVE_UPGRADE_PIP`: whether to upgrade pip during install.
