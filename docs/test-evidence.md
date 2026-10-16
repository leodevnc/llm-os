# Testing

Runtime code has no third-party Python dependencies. Browser tests use Playwright and Chromium.

## Kernel, provider, and HTTP checks

```bash
python3 -m unittest discover -s tests -v
```

Kernel checks cover:

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
schema. This does not verify inference quality, actual model tool selection, or model-specific
schema support.

## Browser workflow

```bash
npm ci
npx playwright install chromium
npm run test:e2e
```

A fresh temporary workspace is created for every suite run. Chromium checks:

1. The Computer home, resident source display, calculator output, exact file approval, six-turn
   completion, memory release, Files view, and persistence after reload.
2. App launch selects local-model mode and the requested manifest, without substituting a demo.
3. The original artifact/memory review sequence and durable output display.
4. Rejection saves no artifact.
5. Document HTML renders literally rather than executing.

The suite captures page errors and checks keyboard navigation and document overflow on desktop
and mobile viewports. It is not a comprehensive accessibility audit.

- [Computer](os-overview.png)
- [Working memory and file review](os-working-memory.png)
- [Mobile Computer](os-mobile.png)
- [Original task flow](workspace.png)

Linux hosts need Chromium system libraries. Playwright's `--with-deps` installer requires suitable
host permissions.

## Packaging and static checks

Build with `python3 -m pip wheel --no-build-isolation --no-deps .`.
The package must include all runtime modules and static HTML/CSS/JavaScript assets.

## Limits

Model accuracy, prompt-injection resistance, multi-user isolation, hardware integration, production
capacity, token-budget correctness, or power-loss durability. File review is authorization, not a
factual correctness check. There is no hosted CI result claimed here.
