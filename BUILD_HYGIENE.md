# Build Hygiene

AXM Universal Creation has one active machine and one authoritative tree.

Normal building does not use a cloned workspace, clean-room copy, merge-back lane, or accumulating staging universe.

A build owns the debris it creates:

`build -> verify -> remove build debris -> confirm clean -> done`

Rules:

- Work on the active machine directly.
- Intended source/state changes remain where they were made.
- Temporary/intermediate files created by a build are removed by that build.
- A workspace-wide destructive clean is not a normal operation.
- A failed build cleans its own temporary material before returning control.
- Daily snapshot recovery is for a genuinely bad machine state, not ordinary build hygiene.

The initial runtime uses `.axm-build/` only for short-lived candidate-test output. That directory is deleted by the same operation that creates it.
