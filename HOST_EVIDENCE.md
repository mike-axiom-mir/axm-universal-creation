# Host Evidence

Deterministic project validation can prove exact file content, parseability, supported static link checks, and Python compilation. It cannot honestly prove that generated code ran, browser controls worked, a visual matched its goal, or gameplay behaved correctly.

`AXM-CAP-BIND-HOST-EVIDENCE` closes the evidence handoff without collapsing that distinction. A browser controller, runtime harness, visual inspector, game host, accessibility checker, person, or another bounded observer may return an attributed observation. Universal Creation checks the envelope and binds it to one exact project body.

## Required binding

A `bind` request contains:

- the project directory;
- a complete map of every current project-relative file to its SHA-256 digest;
- evidence kind: `runtime-execution`, `browser-interaction`, `visual-inspection`, `gameplay-observation`, `accessibility-inspection`, or `host-specific`;
- overall `PASS`, `FAIL`, `UNKNOWN`, or `BLOCKED` status;
- observer identity, ISO-8601 observation time, freshness lifetime, bounded claims, bases, evidence references, limitations, and optional attachment digests.

The current complete project digest map must exactly equal the supplied map. Changed, missing, or additional files reject the receipt. Symbolic links and over-bound project bodies are rejected. An overall `PASS` cannot contain a non-PASS claim, and an overall `FAIL` must name at least one failed claim.

Fresh evidence preserves its supplied effective status. Stale or not-yet-valid evidence preserves the original observation but becomes effectively `UNKNOWN`.

## Meaning

The receipt says that an external observer made these exact claims about these exact bytes during this exact freshness window. It does not say the deterministic core independently ran a browser, judged the image, or granted execution/evolution authority. It creates no automatic activity history.

`examples/requests/inspect_host_evidence.json` inspects the boundary without binding or claiming an observation.
