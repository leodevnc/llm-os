# Architecture

```text
Computer / Tasks / Files UI
          │ goals and exact-content review
          ▼
Loopback HTTP server ───────────────────── SQLite
          │                                ├─ task, epoch, app manifest
          ▼                                ├─ immutable source snapshots
Two-worker cooperative scheduler           ├─ resident page identifiers
          │ one model turn per quantum     ├─ observations and review events
          ▼                                ├─ current files + file history
Context builder                            └─ artifacts + versioned facts
          │ goal + manifest + resident pages + recent observations
          ▼
Local Ollama / explicitly scripted demo
          │ one proposed JSON action
          ▼
Kernel schema, epoch, capability and path checks
          ├─ read / page / calculate ── observation ── requeue
          ├─ persistence proposal ──── review ─────── atomic commit
          └─ finish ──────────────────────────────── completed task
```

## Task lifecycle and scheduling

`ready -> running -> ready` handles a read or computation.
`running -> waiting -> ready` handles a reviewed write.
`running -> succeeded` handles `finish`. Invalid proposals, provider errors, and step exhaustion
end in `failed`. A person can cancel an active task.

A worker claims a task in an immediate SQLite transaction, consuming one step and incrementing
its epoch. Model I/O occurs outside that transaction. Committing the proposal requires the same
running state and epoch; cancellation increments the epoch and fences late responses.

Each worker executes one model turn before returning the task to the queue. Already queued work
gets an opportunity before that task's next turn. A scheduled-ID set avoids duplicate submissions.
There are two slots by default. This is cooperative fairness, not time-sliced preemption: a slow
model call occupies its slot until return or error. Pending reviews occupy no slot. Admission
control, queue quotas, total deadlines, and compute cancellation at the model server are absent.

An advisory lock permits one server per data directory. Restart recovery moves interrupted turns
to ready with new epochs and preserves consumed steps. Pending reviews survive. Recovery may
produce a different model proposal; it does not replay an approved write. Approved effects, their
events, and the state transition share one transaction.

## Applications and authority

Task creation selects a host-owned manifest and stores its snapshot. The model sees the manifest
but cannot change it by emitting arguments. Workspace permits artifacts, facts, and files under
`/notes/` or `/reports/`; Research brief permits only file writes under `/reports/`; Read-only
reviewer has no persistence operation. The task-level write switch can further restrict authority.

Apps share read access. A write namespace is not a confidentiality or tenant boundary. A denied
operation creates a recorded observation and consumes the turn, but causes no proposed side effect.

## Working memory

A task captures source documents at creation. `page_in` stores a document ID in its resident set;
subsequent contexts include that immutable document content. `page_out` removes residency without
deleting the source. When a load would exceed 12,000 source characters, the pager evicts the
least recently explicitly paged-in documents, with document ID as a tie breaker. Loading an already
resident page touches its order. Automatically including a page in context does not touch it.

Resident content reduces the 18,000-character allowance available to recent serialized
observations. The builder walks newest observations first and stops at the first that cannot fit;
it then restores chronological order and reports the omitted count. A single observation above
14,000 characters is omitted. App/goal/inventory/framing and JSON escaping are outside this
approximation. Token-aware budgeting remains future work.

An evicted source remains retrievable from the task snapshot. Residency itself persists across
restart. It is not an isolation boundary or guaranteed erasure from a provider's own caches.
`read` and `fs_read` still use ordinary observation history, not source-page residency.

## Virtual disk and concurrent writes

Paths are validated absolute virtual names; they never reach the host filesystem. Dot traversal,
backslashes, repeated separators, and invalid components are rejected. Only app-approved directory
prefixes can be written. The current-file table holds the latest content/version, while the history
table keeps each approved revision and the originating task/step. Task outputs display their own
revision even if another task overwrites the same path.

A proposal captures the current file version, including version zero for a missing file. Approval
compares it under the write transaction. A conflict leaves the task waiting; reject the old proposal
to let the model continue with new information. Files and facts are read live, unlike source
snapshots. The 100-entry model file listing is bounded; shared file storage and the UI list have no
total quota yet.

The review digest covers task ID, step, exact action, and expected versions. It detects stale UI
decisions, not malicious local callers; it is neither a signature nor authentication.

## Tools and HTTP boundary

Arithmetic walks a whitelist of AST nodes. It allows numbers, parentheses and four arithmetic
operators, with expression length, AST size and intermediate magnitude limits. It does not use
`eval`, import code, or resolve names.

HTTP binds only to `127.0.0.1`, validates Host/Origin, requires a custom header and JSON for writes,
limits request bytes, serves an explicit asset allowlist, and sends a restrictive CSP. UI content
uses `textContent`. These checks reduce browser cross-origin access; they do not authenticate
processes or people sharing the local account.

## Persistence upgrade

Startup adds missing paging/file tables and the app-manifest column. Old tasks use the Workspace
manifest when their stored manifest is empty. Migration is covered by a populated-database test,
not a general schema-versioning framework or a power-loss certification.
