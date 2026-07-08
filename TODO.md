# TODO

## Epic 1: Session runtime

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
  - *dev comment* `ToolCall` lives in `runtime/tool_calls.py` so `messages.py` and `requests.py`
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
prompt visibility foundations (epic 3), UI (epic 4), UI refinement (epic 5),
tool execution (epic 6), disk storage (epic 7), interactive approval UX
(epic 1 only proves the seam works), branching.

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
through the same runtime flow tested in Epic 1.

### Decisions to record in code

- Use an async OpenAI-compatible client, not a sync client wrapped in a worker
  thread.
- The provider boundary owns translation between Dave's `ModelRequest` /
  `StreamEvent` types and SDK payloads.
- `Session` stays provider-agnostic; no OpenAI-specific logic should leak into
  runtime.
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
  provider boundary; avoid ad hoc frozen-json machinery in runtime unless the
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

## Epic 4: Textual UI MVP

Goal: make Dave usable as a small terminal chat UI over the existing headless
`Session`. Keep runtime UI-independent and keep the first UI slice focused on
the linear text conversation path.

Exit criterion:

```bash
dave --fake
```

opens a Textual UI with conversation history above and a prompt input below.
Submitting text streams a model response through `Session.submit_user_message`.

### Decisions to record in code/docs

- Textual is the UI dependency for this slice.
- The UI consumes `Session` events; it does not own message materialization,
  provider translation, or canonical history.
- The first screen is the usable chat surface, not a landing page.
- The prompt input stays at the bottom; conversation output stays above it.
- `dave` should launch the TUI after an explicit provider choice. Keep
  `--version`.
- `dave` should not silently start with the fake provider. Fake mode is useful
  for tests and demos, but must be chosen explicitly with `--fake`.
- Real OpenAI-compatible provider is selected through `--base-url` plus
  optional `--api-key`. `--model` stays as an override; without it Dave detects
  the first model from OpenAI-compatible `/models`.
- Configuration stays minimal. Do not add general config files or env loading
  in this slice; a checked-in smoke TOML for manual UI runs is allowed.
- `ReasoningDelta` should be visible in the simplest useful way, but not as a
  separate debug panel.
- Introduce a small UI presenter/transcript state between runtime events and
  Textual widgets. It maps `SessionEvent`s to display state without deciding
  that reasoning, cancellation, or streaming must always be a specific widget.
- Name the first UI regions/components, such as `ConversationView`,
  `PromptInput`, and `StatusBar`, but keep them as Textual widgets for now. Do
  not create a full framework-neutral UI abstraction in this slice.

### Non-goals for this slice

- no tools or plugin UI
- no raw request/response debug panel
- no branching/history browser
- no persistent session storage
- no full settings system
- no custom theme work beyond a readable default
- no multi-prompt concurrency

### Tasks

- [x] Add Textual dependency
  - update install flow if needed
  - verify `./install.sh` still installs a runnable `dave`
- [x] Define the initial UI design shape
  - conversation/history area
  - bottom prompt input
  - minimal status/error line
  - small presenter/transcript state between `SessionEvent`s and widgets
  - named Textual widgets such as `ConversationView`, `PromptInput`, and
    `StatusBar`
  - no separate debug pane in this slice
- [x] Add Textual app skeleton
  - keep it under a UI package, separate from runtime
  - wire it to an injectable `Session`
  - consume `UserMessageAppended`, `TextDelta`, `ReasoningDelta`,
    `ModelResponseFinished`, `ModelResponseFailed`, and
    `AssistantMessageAppended`
  - *dev comment* `DaveTextualApp` is the event listener/controller,
    `ConversationPresenter` maps runtime events to transcript state, and
    Textual widgets render that state.
- [x] Wire `dave` to launch the MVP UI
  - keep `--version`
- [x] Add minimal provider selection
  - support fake provider for deterministic local startup
  - support explicit `--base-url`, optional `--model`, and optional `--api-key`
  - detect the first OpenAI-compatible model from `/models` when `--model` is
    omitted
  - support optional `--system-prompt`
  - block input while a response is streaming; cancellation remains available
  - *dev comment* fake provider was moved from implicit CLI default to explicit
    `--fake`, because a default fake chat looked like a working real setup.
  - *dev comment* `--model` remains a manual override for endpoints with more
    than one model; autodetection is only a convenience for the common local
    one-model case.
  - *dev comment* OpenAI-compatible model discovery returns the model list;
    CLI currently chooses the first model only when no explicit `--model` is
    passed.
- [x] Add basic in-flight response cancellation
  - keep input disabled while streaming, but keep a cancel shortcut available
  - `Esc` stops the current model response
  - cancellation does not roll back the submitted user message
  - partial assistant/reasoning output may remain visible, clearly marked as
    cancelled, but must not become a completed assistant message
  - no interrupt-with-correction or prompt reopening in this slice
- [x] Add a manual smoke path
  - add a smoke TOML for repeated local UI runs without retyping switches
  - keep the smoke TOML separate from any future real config system
  - document the exact command to launch the UI
  - verify typing a prompt streams a response and leaves the app usable
  - exact command: `.venv/bin/python tests/smoke/textual_ui.py`
  - *dev comment* manually verified against a real endpoint: reasoning and
    answer are visible, and `Esc` cancels an in-flight response.
- [x] Add focused tests only where they carry signal
  - prefer testing UI/session glue over widget internals
  - avoid brittle layout assertions in this first slice
  - *dev comment* current coverage is intentionally flow/integration-heavy:
    CLI selection, provider chunks, session failure, presenter mapping,
    Textual scroll, cancellation, and smoke launcher help.

## Epic 5: Textual UI refinement

Goal: spend a short, feedback-driven pass making the first Textual UI pleasant
to use before moving on to tools/storage/plugins. This epic is allowed to be
more manual and iterative than the runtime/provider slices.

Exit criterion: the MVP UI still does the same simple chat job, but feels good
enough to keep using while developing the next epics.

Status: closed for now. Small UI enhancements may still be interleaved with
later epics, but larger visual/configuration work should become a separate
task or spike.

### Decisions to record in code/docs

- Refinement should improve the existing chat surface, not expand product
  scope.
- Prefer small visual/layout iterations over introducing a full theme/config
  system.
- If visual tuning becomes repetitive or hard-coded, split out a later theme
  configuration spike.

### Non-goals for this slice

- no tools or plugin UI
- no raw request/response debug panel
- no persistent session storage
- no branching/history browser
- no broad config system

### Candidate refinement areas

- [x] Improve message/status visual presentation
  - distinguish user, assistant, reasoning, status, and cancelled/failed states
  - keep rendering simple and terminal-native
  - avoid adding a theme/config system in this slice
  - *dev comment* colors are centralized in `dave.ui.textual.theme` as
    hardcoded gruvbox-dark-ish constants; extract a real theme/config system
    only if more than one theme appears.
- [x] Tune layout spacing and borders
- [x] Tune user/assistant/reasoning presentation
- [x] Keep prompt input usable/focused while streaming
  - allow queued prompts while a response is in flight
  - keep `Esc` as current-response cancellation
- [x] Improve scroll behavior during streaming
  - auto-follow only when already at the bottom
  - preserve user scroll position when reading older output
- [x] Add collapsible reasoning display
  - reasoning starts collapsed
  - streaming reasoning has a slow, subtle label pulse
- optional "reopen interrupted prompt" UX: cancel stream, restore the last user
  text to input, and decide whether that is UI-only draft behavior or canonical
  history edit/branching
- status line and error rendering
- keyboard shortcuts such as quit/cancel/clear if they remain small
- color palette and readability
- screenshot/manual review loop

## Open questions

- How much pluggability do we want? Allow user extensions to emit events
  that e.g. the artifact store should be aware of? How much is too much (e.g.
  if the runtime loses full control of messages[] materialization, we lose debug/branching/compatibility
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
- Add Markdown rendering support for model responses:
  - handle common LLM output such as tables, code blocks, lists, and emphasis
  - decide whether assistant/reasoning text should use the same renderer
  - keep raw text available if Markdown rendering becomes lossy or confusing
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
