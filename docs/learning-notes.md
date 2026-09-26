# Learning notes

- The useful kernel boundary is where a model proposal becomes an action. Formatting a JSON answer
  is insufficient; the host must check the operation, fields, capability, task state, and epoch.
- Cancellation and interruption have different semantics. Cancellation invalidates a task's future
  commits, while restart recovery creates a new attempt with the remaining budget.
- Persistent memory introduces shared mutable state. A version captured at review time makes an
  overwrite conflict visible instead of letting a stale approval silently replace newer data.
- An immutable document snapshot and current memory provide different consistency guarantees.
  The interface and model context should explain which source is being read.
- Demonstration scripts are useful for testing the system boundary, but they provide no evidence
  about a model's ability to choose tools or produce accurate work. Provider and model quality need
  separate evidence.
