# Roadmap

## Initial milestone

- [x] Browser workspace for tasks, documents, memory, and artifacts
- [x] Local model action loop with six typed operations
- [x] Durable state, cancellation fencing, interrupted-turn recovery, step budgets
- [x] Exact write review and version checks for memory
- [x] Explicit scripted demo, kernel tests, local HTTP adapter tests, browser checks

## Questions for a later milestone

- Validate the action loop against an installed local model and a fixed task suite.
- Add token-aware context selection and evidence citations in final answers.
- Design retention and deletion for documents, task snapshots, and memory history.
- Add fair scheduling and an end-to-end deadline for long model requests.
- Define a constrained MCP bridge with per-tool capabilities and observable external effects.
- Consider separate processes for untrusted tool implementations before allowing extensibility.

The current repository does not implement these later capabilities.
