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
