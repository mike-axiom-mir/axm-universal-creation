# Chat lane continuity

This file exists only to clarify repository collaboration history, not machine architecture.

The `axm/chat-creation-decomposer` branch is the working lane for the current AI chat. GitHub permanently closes a pull request after it is merged, so later explicitly requested continuation work from the same chat may reuse the same branch in a new pull request rather than spawning new branches.

The invariant is one active branch/PR lane per chat or AI instance at a time, with fixes and verification kept inside that lane.
