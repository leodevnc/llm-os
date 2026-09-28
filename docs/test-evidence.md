# Test evidence

Verified on 2026-09-28 with Python 3.11.15, Node.js 22.23.2, Playwright 1.63.0 and headless Chromium
under WSL. Runtime code has no third-party Python dependencies.

## Kernel, provider, and HTTP checks

```text
python3 -m unittest discover -s tests -v
Ran 38 tests in 8.157s
OK
```

The new OS checks cover:

- Source-page eviction, explicit touch order, reload, and release without deleting backing data.
- A six-turn scripted research workflow with reviewed file persistence.
- Read-only app enforcement, restricted write namespaces, and invalid app selectors.
- Reading a prior task's file, preserved historical revisions, and stale-review conflict rejection.
- Transaction rollback when event recording fails after a file write.
- Virtual-path validation and rejection of executable or unbounded arithmetic.
- One-worker scheduling order `A, B, A, B` using synchronization events rather than timing guesses.
- An additive upgrade of a populated database missing the app-manifest column.

Existing tests cover concurrent claims, cancelled/duplicate approvals, late responses, restart
epochs, step limits, source snapshots, memory conflicts, malformed actions, context history limits,
and HTTP Host/Origin restrictions. Recovery is tested on persistent SQLite state, not by cutting
power or killing the OS.

The Ollama adapter makes a real HTTP request to a loopback stub and checks its 12-action JSON
schema. No installed local model was available. Inference quality, actual model tool selection,
and model-specific schema support are **not verified**.

## Browser workflow

```text
npm run test:e2e
5 passed (11.0s)
```

A fresh temporary workspace is created for every suite run. Chromium checks:

1. The Computer home, resident source display, calculator output, exact file approval, six-turn
   completion, memory release, Files view, and persistence after reload.
2. App launch selects local-model mode and the requested manifest, without substituting a demo.
3. The original artifact/memory review sequence and durable output display.
4. Rejection saves no artifact.
5. Document HTML renders literally rather than executing.

Both complete workflows capture page errors and assert none. The desktop and 390-pixel mobile
layouts were inspected; tested mobile pages do not overflow horizontally.

- [Computer](os-overview.png)
- [Working memory and file review](os-working-memory.png)
- [Mobile Computer](os-mobile.png)
- [Original task flow](workspace.png)

The in-app Browser connection failed before setup in this environment. Tests used an isolated
headless Chromium process, with NSS/NSPR libraries supplied from a temporary directory. A standard
Linux setup can install prerequisites with Playwright's `--with-deps` option.

## Packaging and static checks

`python3 -m pip wheel --no-build-isolation --no-deps --wheel-dir /tmp/llm-os-wheel .`
successfully built `llm_os-0.2.0-py3-none-any.whl`.
The package includes all runtime modules and static HTML/CSS/JavaScript assets.
Both browser scripts passed `node --check`; `git diff --check` passed.

## What these results do not establish

Model accuracy, prompt-injection resistance, multi-user isolation, hardware integration, production
capacity, token-budget correctness, or power-loss durability. File review is authorization, not a
factual correctness check. There is no hosted CI result claimed here.
