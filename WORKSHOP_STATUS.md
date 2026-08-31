# Workshop Status

The old AXM Workshop is paused and is **not** the foundation of Universal Creation.

Reason: its accumulated build, merge, cleanup, path, and recovery machinery became too fragile and expensive to operate reliably, including for the AI systems that helped design it.

Current order:

1. build the needed capabilities outside the Workshop;
2. prove them in the standalone Universal Creation machine;
3. preserve the standalone machine independently;
4. only then allow a separate, contained attempt to repair the old Workshop using capabilities that already work outside it.

A Workshop repair must not endanger, replace, contaminate, or become a dependency of the standalone machine.

This does not prohibit a narrow, inspectable adapter to a separately running local provider. The existing AXM Local Workshop runtime in `waldo-axm-mirror-research` exposes a native WALDO/OpenAI-compatible loopback bridge. Universal Creation may call that bridge only through its model-independent local-provider contract, with explicit per-request consent and strict response validation. It does not inherit or copy the Workshop body, make the Workshop its control plane, or treat model output as implementation proof.
