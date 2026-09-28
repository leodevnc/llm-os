# Decisions

## One typed action per model turn

A small action vocabulary makes the authority boundary inspectable. The local model can choose
its next action from observations instead of submitting a fixed plan. JSON schema output helps
shape the response, but the kernel validates every operation and field independently.

## Review all persistence proposed by the model

Files, artifacts, and memory can affect later work. Each proposed write pauses with the exact content
visible. This adds interaction cost, but it keeps the first milestone's behavior understandable.
A read-only capability is a server-enforced task setting; a model cannot override it.

## Document snapshots, live versioned memory

Snapshotting documents makes evidence stable during a task. Memory is intended to carry information
between tasks, so reads see current values. The resulting concurrency problem is explicit: a memory
approval must compare the version captured at proposal time. A conflicting review can be rejected,
after which the model receives the rejection and may propose again.

## Store artifacts in SQLite

Putting writes, events, and state changes in one transaction avoids an external-effect ambiguity
in this milestone. The browser can download an artifact after it is saved. Remote APIs and host file
mutation would need a separate design for idempotency and ambiguous outcomes.

## Local model provider plus an honest demo

The default walkthrough is scripted and accepts only its named goal. It exercises real persistence,
review, cancellation, and context behavior. The Ollama adapter is separate and never falls back to
the demo after a failure. This lets execution mechanics be tested without implying that a scripted
answer came from a language model.

## Small runtime surface

Python's standard library and vanilla browser code are enough for the first milestone. The file
lock uses `fcntl`, which targets Linux, macOS, and WSL. Native Windows needs another lock adapter.
The current process is not an adversarial sandbox and does not execute model-provided code.

## Explicit residency before automatic context compression

Source pages have stable IDs and immutable backing content. Explicit load/unload operations make
eviction behavior testable without an extra summarizer model. This costs model turns and uses a
character approximation. Automatic compression and token accounting need separate quality tests.

## Virtual files rather than arbitrary host writes

A SQLite namespace lets approval, version history, the observation, and task state commit together.
It avoids giving generated paths host authority. This is intentionally not a general filesystem:
there are no mounts, symlinks, permissions per file, or rename/delete operations.

## Manifests and one-turn scheduling

Apps currently differ in tool authority, not in hidden personality prompts or installed code.
Persisting the selected manifest makes a task's authority inspectable. All tasks yield after one
model turn so already queued tasks can progress. Hard time limits and process isolation would
require a different execution boundary; the current scheduler makes neither guarantee.
