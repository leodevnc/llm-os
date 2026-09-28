# Learning notes

- The useful kernel boundary is where a model proposal becomes an action. A shaped JSON answer is
  insufficient; the host checks fields, capability, namespace, state, and epoch.
- "Context as RAM" becomes testable when residency is distinct from backing storage. Evicting a
  page should change the next context while leaving its source recoverable. Character budgets
  make the mechanism inspectable but do not predict token consumption reliably.
- File persistence and conversational memory are different interfaces. A report has a path and
  revisions; a recalled fact has a key and value. Both are shared state and need explicit overwrite
  semantics, while source snapshots remain immutable for a task.
- Checking the file version when asking for review is insufficient. Another task can commit before
  the person approves. Comparing again inside the effect transaction prevents a stale overwrite.
- The app manifest belongs to the host, not to generated instructions. Read-only means the kernel
  rejects persistence operations even when the task-level write flag was requested.
- Yielding after one model turn improves queue behavior without losing durable task state. It
  cannot rescue a slot occupied by slow I/O; fairness and deadlines are separate mechanisms.
- Cancellation and restart differ: cancellation fences future commits, while recovery creates a
  new attempt with the remaining step budget. The model's repeated answer need not be identical.
- App namespaces restrict writes, not reads. Shared reads are useful in a personal workspace but
  should never be presented as isolation between mutually untrusted users.
- Fixed demos reveal bugs in the operating environment, not model competence. A real-model goal
  suite remains necessary before claiming that an LLM can reliably use these primitives.
