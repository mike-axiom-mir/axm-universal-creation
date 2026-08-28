# Non-Hidden Contract

The purpose of this contract is to make **structure visible without requiring surveillance**.

## Required for internal creation units

Every internal unit should be discoverable by stable identity and expose, where applicable:

1. identity;
2. purpose;
3. source location;
4. input contract;
5. output contract;
6. dependencies;
7. relationships to other units;
8. implementation kind;
9. current known limitations;
10. current persistent state necessary to understand how the unit exists or behaves.

## Initial implementation kinds

- `DETERMINISTIC_SOURCE`
- `LEARNED_INSPECTABLE`
- `EXTERNAL_BLACK_BOX`
- `HUMAN_SUPPLIED`
- `UNKNOWN`

An `EXTERNAL_BLACK_BOX` must be labelled as such. It may be useful, but the machine may not describe it as internally inspectable.

## What transparency does not require

Transparency does **not** require:

- action logs;
- prompt logs;
- chain-of-thought capture;
- continuous telemetry;
- user-behavior tracking;
- per-step audit trails;
- automatic history accumulation;
- a hidden supervisory model.

The source and live structure explain what the machine **is**. They do not need to record everything the machine **did**.

## Self-modification

A self-modifying machine remains non-hidden only if its **current body** remains inspectable.

Self-created or self-rewritten pieces are held to the same visibility requirement as pieces written by a human or external AI.
