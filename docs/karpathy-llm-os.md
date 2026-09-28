# From the LLM OS analogy to an executable prototype

The starting point is Andrej Karpathy's
[Intro to Large Language Models, LLM OS section](https://www.youtube.com/watch?v=zjkBMFhNj_g&t=2535s),
linked from his [official site](https://karpathy.ai/). His later
[Sequoia Ascent 2026 post](https://karpathy.bearblog.dev/sequoia-ascent-2026/) discusses context as
a program interpreted by a model and a programmable layer of agents. That post identifies itself
as an author-reviewed, AI-generated summary and edited transcript.

These sources motivate an operating-environment analogy, not a concrete compatibility standard.
The mapping below is an engineering interpretation for this repository, not a claim that Karpathy
specified these APIs, limits, or permission mechanisms.

| Analogy | Local implementation | Where it stops |
| --- | --- | --- |
| Model as processor | Ollama emits one proposed JSON action | No claim of deterministic reasoning |
| Context as RAM | Explicit resident source pages and bounded recent observations | Character accounting, not actual model tokens |
| Storage beyond RAM | Immutable source snapshots, shared files and facts | SQLite virtual storage, not host disk access |
| Tools extend computation | Search, arithmetic, file and memory operations | No shell, browser automation, or arbitrary code |
| Programs/apps | Host-owned manifests select tools and writable directories | Not installable third-party applications |
| Processes | Durable tasks yield after one model turn | Cooperative scheduling, not hardware preemption |

## Questions explored

- Can source material be removed from the next context and recovered without losing its backing data?
- Can an application ask for a write without acquiring authority from its own generated text?
- What happens when a pending file review outlives the version it intends to replace?
- Can a multi-turn task yield fairly without discarding its context or execution record?
- Which parts can be checked deterministically before evaluating an actual model?

## Current experiment

The Research brief demo searches evidence, loads a page, computes a value, proposes a file, waits for
human approval, and releases the page. The same kernel accepts model-selected actions through the
Ollama adapter, but the demo itself is a fixed test program. The Computer screen exposes the
resources and active tasks instead of presenting only a chat transcript.

A future milestone should run a fixed goal suite against an installed model, measure valid action
rate and task completion, and report failures as well as successes. Runtime correctness tests
alone cannot answer whether a model uses this environment well.

Device agents, sensors, actuators, and hardware control are outside this project's direction.
