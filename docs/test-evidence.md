# Test evidence

Environment: Python 3.11.15, Node.js 22.23.2, Playwright 1.63.0, Chromium 153, Linux under WSL.
The Python runtime has no third-party dependencies.

## Kernel, provider, and HTTP checks

```text
python3 -m unittest discover -s tests -v
Ran 23 tests in 5.301s
OK
```

The tests cover two separate write reviews in the demo, duplicate and cancelled approvals,
concurrent task claims, late responses after cancellation, epoch changes on restart recovery,
step exhaustion, snapshot reads, reads outside the captured snapshot, versioned memory conflicts,
memory recall, history eviction, read-only capabilities, invalid model actions, and local HTTP
Host/Origin restrictions. Recovery is exercised through a new kernel instance on the persisted
database; it is not a power-loss test.

The Ollama adapter test makes a real HTTP request to a loopback stub, checks the schema and request
options, and validates the returned action. A separate test rejects a cloud model name before any
request. No installed Ollama model was available, so model inference and model-specific schema
compatibility have not been measured.

## Browser workflow

```text
npm run test:e2e
3 passed (7.6s)
```

Each test run starts a server with a fresh temporary workspace. The browser verifies:

1. Search and read lead to an artifact review; approval saves one artifact; a second approval saves
   memory; the task succeeds after five actions; a page reload still shows the artifact.
2. Rejecting the artifact creates no saved artifact and ends the scripted scenario explicitly.
3. HTML placed in a document is rendered literally and does not execute as JavaScript.

The main flow records no page errors. At 390 pixels wide, document width does not exceed the
viewport. [Desktop](workspace.png) and [mobile](workspace-mobile.png) screenshots were inspected.
The desktop Browser connection failed before session setup in this environment, so verification
used an isolated headless Chromium test process. NSS/NSPR libraries were supplied from a temporary
directory; a standard Linux machine can install them with Playwright's `--with-deps` option.

## Packaging

`python3 -m pip wheel --no-build-isolation --no-deps --wheel-dir /tmp/llm-os-wheel .` built
`llm_os-0.1.0-py3-none-any.whl`. Explicit package discovery excludes browser test dependencies and
package data includes HTML, CSS, and JavaScript assets.

## Limits of this evidence

These results validate the modeled runtime mechanics and UI workflow. They do not establish model
accuracy, prompt-injection resistance, multi-user isolation, production capacity, power-loss
durability, or correctness of a model's final claims. Approval authorizes a local write; it does
not verify the content's truth. No hosted CI result is claimed.
