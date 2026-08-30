# Editable Self-Workspace

AXM Universal Creation can clone its complete current source body into a separate editable candidate body.

This is the machine's experimental self-creation lane:

`live source body -> exact candidate clone -> free edits -> candidate build/test -> inspect differences -> separately choose whether to adopt`

The candidate is not the continuing machine. It can diverge, fail, remain unfinished, or accumulate a radically different implementation without changing the live body.

## What the clone contains

The clone operation copies and byte-verifies every included file in the current source body. That includes source, tests, build tools, live capability manifests, anatomy registries, reference material, contracts, examples, state required by the repository, and documentation.

It deliberately does not copy:

- `.git/` history;
- prior `creations/` runtime output;
- `.axm-build/` debris;
- snapshot directories;
- Python and test caches.

Those exclusions keep the candidate a complete editable machine source body rather than a recursive copy of its own outputs or repository history.

Symbolic-link source semantics are not implemented. A source body containing an included symbolic link is rejected instead of silently dereferencing it.

## Operations

The live `AXM-CAP-SELF-WORKSPACE` capability accepts `clone`, `inspect`, `test`, and `request-merge-check`.

Create a candidate body:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/clone_self_workspace.json
```

The included example uses `creations/self-workspaces/first-candidate-body`. A repo-local self-workspace must stay under `creations/`; an absolute path outside the live repository is also supported.

Inspect exact source differences:

```json
{
  "kind": "self-workspace",
  "inputs": {
    "operation": "inspect",
    "path": "creations/self-workspaces/first-candidate-body"
  }
}
```

Run the candidate body's own build and capture its full output:

```json
{
  "kind": "self-workspace",
  "inputs": {
    "operation": "test",
    "path": "creations/self-workspaces/first-candidate-body",
    "timeout_seconds": 900
  }
}
```

The fixed test entrypoint is the candidate's inspectable `tools/build.py`. The result contains exit state, timeout state, standard output, standard error, and the candidate/live source comparison after the build.

The clone is ordinary editable source. Humans, AIs, editors, and current exact text/patch capabilities can change files inside it. No growth score or automatic rewrite loop directs what it should become.

## Candidate-chosen merge check

No check is required after each edit. The clone can experiment for as long as its connected cognition or participants choose.

When the candidate believes it is ready, it may emit a current merge-check request with its own readiness statement and any combination of:

- `source-diff`;
- `build`;
- `machine-inspect`;
- `executable-anatomy`;
- `plan-probes` over candidate-local requests;
- `creation-trials` that create and test real outputs inside the cloned body.

Example:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/request_self_merge_check.json
```

The request state is `MERGE_CHECK_REQUESTED_NOT_APPROVED`. The workspace manager does not decide that the candidate is ready, compute an improvement score, approve the request, or perform a merge. It gathers only the observations the candidate chose and writes the current request to `creations/self-merge-check/current.json` inside the clone. A later request replaces that current state; this is not an accumulating action log.

Planning probes exercise the candidate's current anatomy/direction planner. Creation trials execute the candidate's existing `trial` route in its own cloned body. Additional simulations, organs, hands, learned systems, host capabilities, and physical interfaces can become selectable observations when those capabilities actually exist.

## Truth boundary

This is source-body isolation, not an OS security sandbox. Code run by the candidate build has the current process user's host permissions. The result says this explicitly.

A passing candidate build proves only what that candidate's build currently checks. It does not make the candidate live and does not prove the wider creation direction has been achieved.

Automatic whole-body merge/adoption is not implemented at this milestone. That separation is intentional and visible: the candidate can create, test, inspect, and request observation of itself now; making it the continuing body remains a later explicit choice, to be connected to root fit and daily snapshot recovery without turning experimentation into a guarded permission system.
