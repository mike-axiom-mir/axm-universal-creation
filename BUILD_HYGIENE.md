# Build Hygiene

AXM Universal Creation has one active machine and one authoritative live tree.

Normal changes may still be made and tested directly in that tree. Self-creation experiments may instead use a complete editable candidate-body clone. A candidate clone is not another active machine and does not become authoritative merely by existing or passing its build.

A build owns the debris it creates:

`build -> verify -> remove build debris -> confirm clean -> done`

Rules:

- Work on the active machine directly for ordinary maintenance, or in an explicitly identified self-workspace for whole-body experimentation.
- Intended source/state changes remain where they were made.
- Temporary/intermediate files created by a build are removed by that build.
- A workspace-wide destructive clean is not a normal operation.
- A failed build cleans its own temporary material before returning control.
- Daily snapshot recovery is for a genuinely bad machine state, not ordinary build hygiene.

The runtime uses `.axm-build/` only for short-lived candidate-test output. That directory is deleted by the same operation that creates it.

Persistent editable self-workspaces live at caller-selected locations, normally under `creations/self-workspaces/`. They are creations, not build debris, so normal cleanup does not erase them. See `SELF_WORKSPACE.md`.
