# Daily Snapshot

The rollback model is intentionally small.

Once per day, preserve one complete restorable snapshot of the machine's current state.

A snapshot should contain everything required to restore what the machine **is** at that point, including any source, configuration, capability structure, persistent state, and learned state that the running machine depends on.

It is not an action log and it does not need to explain every change that happened during the day.

New snapshots carry an embedded `axm.universal-creation.snapshot/v1` manifest. The manifest records the exact payload file set, byte counts, and SHA-256 for every stored file. Snapshot verification checks canonical archive paths, duplicate/colliding entries, ZIP CRCs, the declared file set, byte counts, and payload hashes before a restore is allowed to move the current body into quarantine. The manifest is recovery metadata and is not restored into the live machine body.

Use the independent read-only verifier before a restore when useful:

```bash
PYTHONPATH=src python -m axm_uc snapshot verify /path/to/AXM_Universal_Creation_YYYY-MM-DD.zip
```

Older snapshots created before the manifest contract remain restorable for continuity. They are explicitly reported as `legacy-zip` / `zip-crc-only`; they do not inherit the stronger per-file SHA-256 claim retroactively.

If a later state behaves badly or a change proves unwanted:

1. verify the selected snapshot;
2. quarantine the current day's state;
3. inspect it separately if useful;
4. restore a known-good earlier daily snapshot.

The restore boundary never permits snapshot payloads to overwrite the live repository's preserved `.git` state or other snapshot-excluded internal/cache directories.

No per-step logs, merge bureaucracy, automatic canon system, or event-history machinery is required by this design.

The daily snapshot is the recovery boundary, not the machine's intelligence and not an incentive shaping its behavior. SHA-256 and ZIP verification establish payload integrity within this contract; they do not prove authorship, correctness, safety, or that a snapshot is actually known-good.
