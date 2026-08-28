# Daily Snapshot

The rollback model is intentionally small.

Once per day, preserve one complete restorable snapshot of the machine's current state.

A snapshot should contain everything required to restore what the machine **is** at that point, including any source, configuration, capability structure, persistent state, and learned state that the running machine depends on.

It is not an action log and it does not need to explain every change that happened during the day.

If a later state behaves badly or a change proves unwanted:

1. quarantine the current day's state;
2. inspect it separately if useful;
3. restore a known-good earlier daily snapshot.

No per-step logs, merge bureaucracy, automatic canon system, or event-history machinery is required by this design.

The daily snapshot is the recovery boundary, not the machine's intelligence and not an incentive shaping its behavior.
