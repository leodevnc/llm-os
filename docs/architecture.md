# Architecture

```text
Browser workspace
    │ task goal / review decision
    ▼
Loopback HTTP server ───── SQLite workspace
    │                         │
    ▼                         ├─ task + captured documents
Two worker slots              ├─ action observations / review record
    │                         ├─ approved artifacts
    ▼                         └─ versioned memory
Context builder
    │ system contract + goal + document inventory + recent observations
    ▼
Local Ollama / labeled scripted demo
    │ one proposed JSON action
    ▼
Schema + capability checks
    ├─ search / read / recall ── observation ── next turn
    ├─ write / remember ─────── human review ── atomic save + observation
    └─ finish ──────────────── completed task
```

## Task lifecycle

`ready -> running -> ready` handles reads. `running -> waiting -> ready` handles a reviewed write.
`running -> succeeded` handles `finish`. A malformed proposal, provider error, or exhausted step
budget ends in `failed`. A person may transition an active task to `cancelled`.

A worker claims a ready task in an immediate SQLite transaction. The claim consumes a step and
increments an epoch. The model request happens outside the transaction. The kernel commits its
response only if the task is still running with that epoch. Cancellation increments the epoch.
This prevents a slow response from acting after cancellation without holding a database lock while
the model works.

The process holds an advisory file lock for its data directory. After acquiring it on restart, the
server moves interrupted running tasks back to ready and increments their epochs. Waiting reviews
remain waiting. Recovery repeats a model turn, which may produce a different proposal. It does not
replay an approved write, because approved writes and their state transitions share a transaction.

## Data boundaries

Documents are copied into a task snapshot at submission. A document added later is absent from that
task, even if the model guesses its ID. Search is deterministic lexical matching over the snapshot.
Memory is read live through `recall` and includes its version. A memory proposal records the current
version; approval fails if another task changed that key in the meantime.

An approval digest covers task ID, step, exact action, and expected memory version. It prevents
ordinary stale or mismatched UI approval. It is not a signature or a credential. The local caller
and database owner are trusted. Artifacts are rows in the workspace database; model-supplied titles
and content never become host filesystem paths.

## Context and budgets

The model gets the immutable goal, a bounded document inventory, write capability, remaining step
count, and recent observations. Observations are included newest-first within an 18,000-character
history budget, then restored to chronological order. A single observation above 14,000 characters
is omitted. The context explicitly counts omitted observations. This is a teaching approximation;
different models need token-aware budgeting and framing overhead.

The UI uses ten steps per task; the core accepts one to twenty. Two workers may execute separate
tasks concurrently. Queue scheduling is simple and a long task can occupy a slot until review or
completion. Socket timeouts bound stalled I/O, not total wall time against a peer that keeps sending
bytes slowly. Model compute may continue after local cancellation; the epoch check prevents its
result from affecting the cancelled task.

## HTTP boundary

The server binds only `127.0.0.1`. It checks Host and Origin, requires a custom header plus JSON for
writes, caps request bytes, serves an explicit asset allowlist, and sends a restrictive CSP. These
checks reduce browser cross-origin access; they do not authenticate other processes on the machine.
The UI renders model and document content with `textContent`.
