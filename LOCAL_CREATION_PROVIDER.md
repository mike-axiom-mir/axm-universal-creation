# Local Creation Provider

Universal Creation can use an existing local model to propose missing software-project files or execute a prepared stepwise perspective checkpoint without importing that model or its host into the deterministic core.

The live boundary is `AXM-CAP-LOCAL-CREATION-PROVIDER`. Its transport is an OpenAI-compatible `POST /chat/completions` endpoint on explicit loopback HTTP only. The known compatible AXM provider is the Local Workshop native WALDO bridge, normally at `http://127.0.0.1:7789/v1`. Another explicitly selected local provider, such as LM Studio, may use the same contract.

## Truth and authority boundary

- No provider call occurs unless the request contains `provider.allow_call: true`.
- The endpoint must use `127.0.0.1`, `localhost`, or `::1`; cloud endpoints are rejected.
- A provider proposes bounded UTF-8 project files. It does not select the destination, install anything, adopt a candidate, mutate CANON, change permissions, or write the machine body.
- The host accepts only the exact response schema, safe project-relative paths, at most 128 files, and at most 2 MiB of UTF-8 file content.
- The existing project builder stages and validates the proposal before publication. A separate validation pass rechecks the materialized files.
- Structural and digest validation does not prove runtime, browser, visual, gameplay, user-experience, or general semantic correctness.
- Request, raw response, and normalized proposal digests remain visible. The model may still produce different proposals for the same request.
- `analyze-checkpoint` accepts only an exact digest-bound workflow and prepared checkpoint, requires the provider to return every expected specialist id under a strict schema, and passes the response through the existing deterministic checkpoint validator.
- When one local provider applies several specialist profiles, the receipt labels this as one cognition using several method overlays. It does not claim several independent identities or independent evidence sources.

## Planning behavior

An exact route is now reported as ready only when its required inputs are present. For example, this is an input gap, not coverage:

```json
{
  "kind": "static-web-project",
  "direction": "create a playable local strategy game",
  "inputs": {"path": "creations/strategy-game"}
}
```

Because only `files` is missing, the result exposes a provider bridge but makes no call. To authorize the existing local provider for this request, add a top-level provider selection:

```json
{
  "kind": "static-web-project",
  "direction": "create a playable local strategy game",
  "inputs": {"path": "creations/strategy-game"},
  "provider": {
    "endpoint": "http://127.0.0.1:7789/v1",
    "model": "waldo",
    "allow_call": true
  }
}
```

This bridge applies only to bounded project routes whose sole missing input is `files`. The same capability can be invoked directly with `kind: provider-backed-project` and `operation: create`.

Use `examples/requests/prepare_local_creation_provider.json` to inspect the exact request contract without making a provider call.
