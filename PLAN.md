# PLAN

## Compass

Dave is a local agent workbench: a UI-independent runtime for interactive LLM
sessions, built around inspectable requests, evented state, tools, plugins,
traces, and branchable conversations.

The user stays in control. The system should make model interaction easier to
see, shape, debug, and extend. Every important decision should be inspectable and overridable.

## Epics

0. Domain model spike
1. Core session runtime
2. Model client and stream adapter
3. Event log and message materialization
4. Request/response debug visibility
5. Trace and artifact storage
6. Textual UI
7. Tool registry and tool execution
8. Plugin and hook system
9. Context compaction
10. Conversation branching
11. Multi-agent sessions
12. Workflow/state graph
13. Extension documentation

## Notes

- Domain model spike should settle initial shapes for `Session`, `Branch`, `Event`,
  `Message`, `ChatRequest`, `StreamEvent`, `ToolCall`, and `ArtifactRef`.
- Epics are ordered by intended implementation sequence.
- Core must stay independent from UI.
- `messages[]` should be a materialized view, not the source of truth.
- Early debug means raw request/response visibility, not the full trace system.
- Debug visibility should be built from the same request/response objects used by the runtime, not reconstructed from SDK internals.
- `build_request()` and `send_request()` should be separate operations from the start.
- Canonical event log means semantic session events.
- Trace/artifacts means raw payloads, chunks, requests, responses, and large tool outputs.
- Plugins should intercept behavior without coupling core to Textual.
- First implementation slice should be headless.
