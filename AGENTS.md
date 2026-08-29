# AXM Universal Creation — Builder Guidance

This repository represents one standalone machine.

## Current truth

`main` is the authoritative shared GitHub state.

GitHub is a publication and collaboration surface, not a required heartbeat for the machine. Local or other active builds may move faster than GitHub. Do not infer that a capability does not exist merely because a public push has not caught up.

## Working style

There is **no mandatory PR-lane system** and no merge ritual required by the machine.

A builder may use a branch when isolation is technically useful, but branches are ordinary Git tooling, not governance or safety machinery. When work is verified and integration is requested, it may be incorporated into `main` directly.

Do not create cleanup branches, merge-back branches, duplicate machines, or extra process merely to satisfy a workflow convention.

## Build responsibility

A build owns temporary debris it creates:

`build -> verify -> remove temporary debris -> done`

Intended source and state changes remain part of the active machine. Daily snapshot recovery is the recovery boundary for a genuinely bad machine state.

## Direction

Do not silently reintroduce the old Workshop architecture, logging systems, hash baselines, automatic governance, or forced agent architecture.

The machine may inspect and modify itself. Self-modification passes the four-root fit step:

**Truth · Agency · Continuity · Wisdom Before Speed**

Growth is an outcome, not a benchmark or reward.
