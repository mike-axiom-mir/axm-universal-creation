# Internal Integrity

The machine may use hashes internally to detect unexpected changes, corruption, missing body files, or an out-of-date baseline.

Integrity is a property of machine state, not a judgement about a human, AI, tool, or other participant.

A mismatch means: inspect this state.

It does **not** mean: mark the participant untrusted, block unrelated creation, require a merge ritual, or force a human to repair hash bookkeeping.

The initial runtime keeps an inspectable SHA-256 body manifest in `state/integrity.json`. Ordinary creation is not blocked merely because the manifest reports a changed file. The integrity view exists to help the machine locate what changed and to support recovery/verification.
