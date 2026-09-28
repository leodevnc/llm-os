# Roadmap

## v0.1: local action loop

- [x] Browser workspace for tasks, documents, memory, and artifacts
- [x] Local Ollama adapter and six initial typed operations
- [x] Durable state, cancellation fencing, recovery, and step budgets
- [x] Exact write review and version checks for memory
- [x] Explicit scripted demo and kernel, HTTP, and browser tests

## v0.2: operating-environment primitives

- [x] Model-addressable source paging, eviction, and reload
- [x] Versioned virtual files shared across tasks
- [x] Host-owned app manifests and per-app write namespaces
- [x] Bounded arithmetic without arbitrary code execution
- [x] One-turn cooperative scheduling
- [x] Computer overview, working-memory inspection, and Files view
- [x] Six-turn scripted OS walkthrough and migration/regression coverage

## Next experiment: model behavior

- [ ] Run a reproducible goal suite against an installed local model.
- [ ] Record tool validity, completion, denied actions, and unsupported claims.
- [ ] Compare explicit paging with history-only context on the same evidence tasks.
- [ ] Add token-aware budgeting after choosing and measuring a model.

## Later questions

- Add bounded task admission, storage quotas, and end-to-end model deadlines.
- Design retention and deletion across source snapshots, pages, and file history.
- Add evidence references to final answers and a file-version inspection interface.
- Explore a constrained MCP bridge only after specifying its external-effect boundaries.

Device control and a bootable operating system are not planned.
