# Events

Dave uses events for three different jobs. Keep these families separate.

## Event Families

Canonical events are durable semantic session history. They are the source of
truth for message materialization, branching, audit, and restoring Dave's
session view.

Stream events are live runtime notifications. UI, CLI, and debug consumers can
render them immediately, but restoring the session view should not depend on
them.

Debug events are stream events with inspectable runtime views. They are built
from the same objects used by the runtime, not from SDK internals. They are not
raw HTTP or wire-level traces.

## Current Events

| Event | Family | Canonical | Meaning |
| --- | --- | --- | --- |
| `SystemPromptSet` | canonical | yes | Active session system prompt was set or replaced. |
| `UserMessageAppended` | canonical | yes | User text became durable session history. |
| `RequestApproved` | canonical | yes | A candidate request was accepted for sending; payload lives behind an artifact ref. |
| `RequestRejected` | canonical | yes | A candidate request was rejected and will not be sent. |
| `AssistantMessageAppended` | canonical | yes | Assistant output became durable session history. |
| `ToolResultAppended` | canonical | yes | Tool result became durable session history; large result data lives behind an artifact ref. |
| `ModelResponseFailed` | canonical | yes | An approved request failed before a durable assistant message was appended. |
| `RequestBuilt` | stream | no | Dave built a provider-neutral `ChatRequest` candidate. |
| `RequestSent` | stream | no | Dave started sending the approved `ChatRequest`. |
| `TextDelta` | stream | no | Model response text streamed from the provider adapter. |
| `ReasoningDelta` | stream | no | Model reasoning text streamed from the provider adapter. |
| `ModelResponseFinished` | stream | no | One model response finished streaming. |

## Planned Debug Events

| Event | Family | Canonical | Meaning |
| --- | --- | --- | --- |
| `DebugRequestReady` | debug stream | no | Inspectable request view for debug UI/logging, including the runtime request and provider-call-ish payload. |
| `DebugResponseReady` | debug stream | no | Inspectable response view assembled while processing the same stream that emits text/reasoning deltas. |

Debug events expose Dave/runtime-level views. They do not promise raw provider
chunks, HTTP headers, SDK retries, or exact network bytes. Serious wire-level
tracing should be a separate trace/proxy/HTTP-hooks feature.

Restoring Dave's session view means reconstructing Dave's messages, requests,
and decisions. It does not mean re-executing external side effects such as tool
calls that changed files or other systems.

Reading historical events is read-only. Tool execution and other side effects
happen only in live runtime flows, not when consumers inspect past events.
