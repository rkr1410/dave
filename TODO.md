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
  `ModelRequest -> Approve(request) | Reject(reason)`), defaulting to
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
  - other: `Message`, `ModelRequest`, `ArtifactRef`, `ToolCall`, `Approve`,
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
  - accepts `ModelRequest`
  - streams deterministic chunks
  - can simulate failure for tests
- [x] Implement `Session.submit_user_message()` happy path
  - append `UserMessageAppended`
  - materialize messages
  - build `ModelRequest`, emit `RequestBuilt`
  - call the approver (default auto-approve), append `RequestApproved`
  - on reject: append `RequestRejected`, yield it, end the generator —
    nothing is sent
  - send, emit `RequestSent`
  - stream `TextDelta`, accumulate assistant draft
  - emit `ModelResponseFinished`
  - append and yield `AssistantMessageAppended` (last event of the
    iteration — the durable-commit signal consumers refresh on)
  - *dev comment* the approved request artifact is an in-memory
    provider-neutral `ModelRequest` snapshot for now, not the final serialized
    debug schema
- [x] Handle provider failure
  - append `ModelResponseFailed` with error/partial-output artifact refs
  - leave `partial_output_ref` empty when the provider fails before any
    `TextDelta`
  - do not append a partial `AssistantMessageAppended`
  - yield `ModelResponseFailed` and end the generator normally
- [x] Add tests
  - happy path event order
  - message materialization
  - request is built before sent
  - approved request is the sent request
  - an approver that edits the request → the edited request is sent
  - a rejecting approver → `RequestRejected` appended, nothing sent, no
    assistant message
  - failure does not append a partial assistant message
  - failure event carries refs that resolve in the artifact store
  - *dev comment* covered with a small number of flow-style `unittest` cases
    instead of narrow unit tests for each method
- [x] Skip CLI smoke command
  - *dev comment* fake-provider output would add little signal before the real
    model client/debug visibility work, so Epic 1 closes without this optional
    layer

Out of scope (later epics): real OpenAI-compatible client (epic 2), request/
response debug visibility (epic 3), UI (epic 4), disk storage (epic 5), tool
execution (epic 6), interactive approval UX (epic 1 only proves the seam works),
branching.

## Epic 2: OpenAI-compatible provider MVP

Goal: make the existing headless `Session` exchange streamed text with a real
OpenAI-compatible endpoint. Keep the runtime UI-independent and keep the slice
small: no tools, no persistent trace store, no debug panel, no provider registry.

Exit criterion:

```python
session = Session(
    model="gpt-4.1-mini",
    provider=OpenAICompatibleProviderClient(
        base_url="http://localhost:1234/v1",
        api_key="dummy",
    ),
)

async for event in session.submit_user_message("hello"):
    ...
```

streams real `TextDelta` events and appends a real `AssistantMessageAppended`
through the same core flow tested in Epic 1.

### Decisions to record in code

- Use an async OpenAI-compatible client, not a sync client wrapped in a worker
  thread.
- The provider boundary owns translation between Dave's `ModelRequest` /
  `StreamEvent` types and SDK payloads.
- `Session` stays provider-agnostic; no OpenAI-specific logic should leak into
  core.
- Configuration is explicit for this slice: pass `base_url`, `api_key`, and
  model deliberately. Environment variable loading can come later.
- Debug visibility must later use the same request/response objects that the
  provider sends and receives; do not reconstruct debug data from unrelated SDK
  internals.

### Tasks

- [x] Add the OpenAI SDK dependency
  - use the async client API
- [x] Add OpenAI-compatible provider slice
  - create from explicit constructor args
  - require `base_url`
  - accept optional `api_key`, with a harmless dummy default for local
    OpenAI-compatible endpoints that require the field but ignore the value
  - convert `ModelRequest` to OpenAI-compatible messages
  - support text-only `system`, `developer`, `user`, `assistant`, and `tool`
    roles if they are already present in `Message`
  - keep tool-call serialization minimal or explicitly unsupported if it would
    expand the slice
  - convert raw streamed chunks to Dave `TextDelta`
  - convert `reasoning_content` chunks seen in local Gemma/Qwen probes to Dave
    `ReasoningDelta`
  - ignore empty/no-op chunks
  - ignore role-only chunks, finish reasons, usage, and local `timings` metadata
    until debug/trace work needs them
  - preserve a short useful error message for `ModelResponseFailed`
  - request serialization
  - stream adapter behavior
  - provider error mapping
- [x] Tighten message modeling before closing the provider slice
  - add Pydantic as a direct dependency
  - replace the loose `Message(role=...)` dataclass with concrete message types
    and a discriminated union
  - make `ToolMessage` require `tool_call_id`
  - keep assistant tool-call serialization explicitly unsupported for this slice
  - map Dave message types to OpenAI message params in the provider adapter
  - *dev comment* provider serialization exposed that the old one-class
    `Message` shape allowed impossible states such as tool messages without
    `tool_call_id`; when roles imply different required fields, model them as
    distinct types instead of checking string roles at the boundary.
- [x] Add real-provider smoke script
  - add `tests/smoke/openai_compatible.py`
  - add `tests/smoke/openai_compatible.toml` with explicit `base_url`,
    `api_key`, and `prompt`
  - auto-detect the model from `{base_url}/models`
  - stream `Session.submit_user_message(...)` and print event types/content
  - run manually against a configured OpenAI-compatible endpoint
  - do not wire this into `unittest`

### Review questions

- Decide whether provider-facing request/response/debug schemas should use
  Pydantic models instead of plain dataclasses.
- Decide JSON argument validation/serialization for `ToolCall.arguments` at the
  provider boundary; avoid ad hoc frozen-json machinery in core unless the
  boundary actually needs it.
- Decide how much OpenAI-compatible variance to tolerate in the MVP before it
  becomes a provider compatibility project.
- Decide when, if ever, to add environment variable loading such as
  `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or a default model.

## Epic 3: Request/prompt visibility foundations

Goal: keep the early request path inspectable enough for headless/UI work by
documenting event families and closing the immediate system-prompt gap.
Do not add request/response debug events in this slice.

Exit criterion:

```python
async for event in session.submit_user_message("hello"):
    ...
```

includes the active system prompt in built/approved request snapshots. Event
docs explain the current event families and the boundary between runtime views
and later wire-level tracing.

### Decisions to record in code/docs

- System prompt is session/branch state, not something the UI should manually
  prepend on every submit. Add a canonical event such as `SystemPromptSet`, and
  have `build_request()` prepend the active `SystemMessage` when one is set.
- Runtime-level debug events are deferred. Names like `DebugRequestReady` and
  `DebugResponseReady` remain possible extension points, but should not be
  added until we decide whether runtime-ish views are worth having.
- The stronger original wish is raw request/response visibility. That likely
  belongs to later trace/proxy/HTTP-hooks work, not Session-level synthetic
  events.
- Request editing is deferred. Changing existing conversation messages should
  require branching/correction canonical events, not only an edited approved
  request snapshot that diverges from session history.
- Canonical event log remains semantic session history only.
- Request-local developer messages are a future idea, not part of this slice:
  later request modifiers/hooks may inject them after `RequestBuilt` and before
  `RequestApproved`, and the accepted `ModelRequest` snapshot should preserve
  whatever was finally sent.

### Tasks

- [x] Start event documentation
  - add `docs/events.md`
  - describe event families: canonical events, stream events, debug events
  - add a compact table for existing event names, family, meaning, and whether
    they are canonical
  - document that future debug events would expose inspectable runtime views,
    not raw HTTP
- [x] Add session system prompt support
  - add a canonical system-prompt event such as `SystemPromptSet`
  - expose a small session API for setting/replacing the active system prompt
  - prepend the active system prompt as the first `SystemMessage` in
    `build_request()`
  - keep the resulting system message visible in `RequestBuilt` and the
    approved request snapshot
- [x] Defer request/response debug event API
  - do not add `DebugRequestReady` / `DebugResponseReady` in this slice
  - keep debug events available as a future extension point
  - move raw request/response visibility to later trace/proxy/HTTP-hooks work
  - *dev comment* the original wish was closer to raw wire visibility than
    runtime-ish debug objects; synthetic Session events would be a half-step
    unless/until we decide they are useful on their own.

## Open questions

- How much pluggability do we want? Allow user extensions to emit events
  that e.g. the artifact store should be aware of? How much is too much (e.g.
  if the core loses full control of messages[] materialization, we lose debug/branching/compatibility
  without the exact plugin versions)

## Soon after Epic 1

- If first real use shows that Dave needs simple `list_files` / `read_file`
  tool calls to be useful, add a small spike for the
  cheapest coherent path: enough to work, without falling into the full tool
  registry/plugin implementation.

## Later

- Define history/read API semantics:
  - reading historical events is read-only
  - tool execution and other side effects happen only in live runtime flows
  - do not design full event-sourcing/idempotent side-effect replay unless it
    becomes a real requirement
- Explore request-local developer messages as a request modification mechanism:
  a future hook/plugin could inspect `RequestBuilt`, inject a `DeveloperMessage`
  before `RequestApproved`, and let `RequestApproved` record the final accepted
  `ModelRequest` without making the developer message durable session history.
- Revisit request/response visibility:
  - decide whether Dave needs runtime-level debug events, raw wire-level
    tracing, or both
  - if runtime-level debug events are useful, define names like
    `DebugRequestReady` / `DebugResponseReady` with explicit "not raw HTTP"
    semantics
  - if raw wire visibility is the real goal, explore proxy, HTTP hooks, or SDK
    trace capture instead of synthetic Session events
  - define request editing semantics before exposing editable debug requests;
    editing existing conversation messages likely belongs with branching or
    correction canonical events
- Revisit OpenAI-compatible provider API choice:
  - compare Chat Completions and Responses API after more local/provider
    testing
  - check whether Responses API gives better typed reasoning/output structure
    for local OpenAI-compatible endpoints
  - keep current Chat Completions implementation unless the comparison shows a
    clear benefit
- Survey opencode and pi.dev coding-agent features:
  - look for useful capabilities Dave should consciously keep room for
  - focus on extension points and architecture pressure, not scope expansion
  - capture any strong ideas as future spikes before implementation
- Decide how large files or long pasted user text should enter model requests:
  inline content, artifact-backed message parts, summaries, provider uploads, or
  another representation.
  - Consider artifact metadata/enrichment for large pasted text/files, e.g. an
    async side pass that summarizes or classifies artifacts so users can later
    refer to "the file with xyz".
- Add optional install settings:
  - `DAVE_BIN_DIR`: directory for the global `dave` wrapper.
  - `DAVE_VENV_DIR`: virtualenv path.
  - `DAVE_INSTALL_ROOT`: directory for commit install snapshots.
  - `PYTHON_BIN`: Python executable used to create the venv.
  - `DAVE_UPGRADE_PIP`: whether to upgrade pip during install.
