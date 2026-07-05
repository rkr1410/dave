# PLAN

## Compass

Dave is a local agent workbench: a UI-independent runtime for interactive LLM
sessions, built around inspectable requests, evented state, tools, plugins,
traces, and branchable conversations.

The user stays in control. The system should make model interaction easier to
see, shape, debug, and extend. Every important decision should be inspectable and overridable.

## Epics

0. Domain model spike
1. Headless session runtime MVP
2. OpenAI-compatible provider MVP
3. Request/response debug visibility
4. Textual UI MVP
5. Persistent event/trace/artifact storage
6. Tool registry and tool execution
7. Plugin and hook system
8. Context compaction
9. Conversation branching
10. Multi-agent sessions
11. Workflow/state graph
12. Extension documentation

## Notes

- Domain model spike should settle initial shapes for `Session`, `Branch`, `Event`,
  `Message`, `ChatRequest`, `StreamEvent`, `ToolCall`, and `ArtifactRef`.
  Current spike output lives in `DOMAIN.md`.
- Epics are ordered by intended implementation sequence.
- Epic 1 includes the first in-memory event log, message materialization, and
  artifact store. Later storage work means persistence and richer trace/debug
  data, not inventing those concepts from scratch.
- Core must stay independent from UI.
- `messages[]` should be a materialized view, not the source of truth.
- Session-level input shaping, such as the active system prompt, is semantic
  session/branch state and must be visible in built/approved requests.
- Early debug means raw request/response visibility, not the full trace system.
- Debug visibility should be built from the same request/response objects used by the runtime, not reconstructed from SDK internals.
- `build_request()` and `send_request()` should be separate operations from the start.
- Canonical event log means semantic session events.
- Trace/artifacts means raw payloads, chunks, requests, responses, and large tool outputs.
- Plugins should intercept behavior without coupling core to Textual.
- First implementation slice should be headless.
- The tool loop *shape* is sketched in `DOMAIN.md` before the UI epic, but tool
  execution stays in epic 6. The UI MVP targets the linear happy path
  (send text -> model response) without contradicting the loop shape.
