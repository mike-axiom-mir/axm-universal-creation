# Host Adapters

AXM Universal Creation is intended to be a standalone inner creation body that can later be embedded in different hosts.

Possible hosts include software applications, AI systems, games, local devices, robots, fabrication hardware, or future systems not yet designed.

The core should not be rebuilt for every host. A host adapter should expose the environment in an inspectable contract, for example:

- available inputs/sensors;
- available actions/tools;
- state/storage locations;
- creation/output channels;
- host-specific limits.

The host remains its own system. AXM does not require ownership of the host to connect to it.

The self-workspace readiness hook follows the same boundary. A future AI, game, OS, robot, fabrication system, or other host cognition may choose when to request candidate observations. The current deterministic workspace capability exposes that request surface but does not pretend to supply the host's judgment, simulation, sensors, or final adoption choice.

Two live boundaries now make that separation executable:

- `AXM-CAP-LOCAL-CREATION-PROVIDER` sends an explicitly authorized proposal request only to a caller-selected loopback OpenAI-compatible provider. AXM Local Workshop's native WALDO bridge is one known compatible host. The provider returns candidate UTF-8 files, not authority or proof.
- `AXM-CAP-BIND-HOST-EVIDENCE` accepts attributed runtime, browser, visual, gameplay, accessibility, or host-specific observations only when they bind to the complete current project digest map. It checks structure, consistency, and freshness but does not relabel an external observation as one performed by the deterministic core.

See `LOCAL_CREATION_PROVIDER.md` and `HOST_EVIDENCE.md`.
