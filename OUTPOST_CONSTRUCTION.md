# Outpost placement and resources

This extends the existing browser-arena generator with an optional `construction`
contract. The unchanged Signal Keep demo remains alongside a separate generated
Signal Outpost. No extra live capability or installed organ is claimed.

Reproduce from the repository root:

```
PYTHONPATH=src python -m axm_uc create examples/requests/create_outpost.json
```

For regeneration, set `inputs.replace` to true in a request copy. The generator
validates and emits the same closed game specification, media, renderer and
project evidence as other arenas. It adds the optional construction controls.

## Reusable operations

`Construction.create`, `canPlace`, `place`, `tick` and `reward` have no Canvas or
DOM dependency. They operate on a validated catalog/grid and explicit state.
Placement checks integral grid coordinates, bounds, reserved/occupied cells and
credit sufficiency before changing anything. Accepted placement deducts the cost
once. Rejected placement does not alter buildings, credits or elapsed ticks.
Income uses explicit integral ticks and a bounded credit total.

The browser adapter additionally rejects cells occupied by current units. Core
footprint and initial player cell are reserved during normalization; the example
also reserves lanes and decorative fixtures. The adapter runs income, turret fire
and in-range core repairs each simulated second, only during play. Pause stops
those effects. Reset restores the initial budget and removes placed buildings.
Combat rewards also add spendable credits while combat score stays separate.

The renderer reuses projection, depth ordering, material boxes, shadows, glow,
and the cached static floor. Support structures remain dynamic scene objects so
new construction never contaminates the static cache. Selecting a building shows
the placement grid; existing support ranges are shown while constructing.

## First demonstration

Start with 200 credits. A generator costs 60 and earns 6 credits per simulated
second; a turret costs 90 and deals 25 damage per second to a nearby enemy; a
repair station costs 50 and restores 5 core health per second within its range.
Choose a building, select an allowed grid cell, then Return to combat and Start.
The player can still move and shoot using the existing controls.

Buildings currently occupy one grid cell for placement. They are support fixtures:
they do not obstruct unit movement or take damage. There is no navigation grid,
selling, upgrades, repair of other buildings or saved session
yet. A lost core cannot be resurrected by a repair tick. This is the agreed first
placement/resources stage, not a completed RTS or tycoon generator.

## Evidence — 2026-09-12

- Full build: 456 tests passed, BUILD_OK (27.119 seconds).
- Focused tests: 9 passed. New checks cover normalization round-trip, invalid
  fields, input preservation, atomic rejection, exact spend/income, reward cap,
  generator/turret/repair integration, pause and reset.
- Actual Chrome placement: generator reduced 200 credits to 140; clicking the
  same cell again reported occupied with 140 credits and one building retained.
  Three purchases spent exactly 200; another purchase reported insufficient funds
  with zero credits and three buildings retained.
- Final Chrome build: all three structures placed and rendered. Income advanced
  0 -> 6 -> 12. Without player shots (18/18 ammunition), Scout 01 health fell to
  10/60 from turret support. Pause entered the paused state.
- Repair math, reset economy, and pause invariants are checked in executable
  runtime tests; no claim of browser-observed repair animation or physical-phone
  multitouch. No browser frame-rate benchmark or complete round certification.

Truth keeps supplied design, pure operations, generator validation and browser
observations distinct. Agency preserves explicit start/pause and building choices.
Continuity keeps the arena path and older demo. Wisdom before speed limits this
pass to the working placement/economy/support contract and names missing systems.

## Three-wave pass — 2026-09-12

The optional validated `waves` plan adds three explicitly launched waves to Signal
Outpost. Each clear grants 60 credits; between waves the simulation pauses for
building. Launch preserves structures, credits, score, player position and core
health, replenishes ammunition, and recreates enemies from the original roster.
Health rises 25% and speed 10% of base per wave. Original enemy arrival cells
remain unavailable for construction. The third clear ends in victory.

Full build: 458 tests passed, BUILD_OK (25.227 seconds). Runtime tests cover
carryover, duplicate-clear rejection, paused income, explicit launch, enemy
scaling, arrival reservations, final victory, simultaneous core loss and reset.
Chrome completed all three waves through visible controls in a temporary generated
one-enemy, low-health fixture: 270, 340, then 410 credits including kill rewards.
This verifies browser transitions, not the full outpost's difficulty or a physical
phone. The fixture is excluded from the published site.

## Authored encounter rosters — 2026-09-12

The optional `waves.rosters` field accepts exactly one nonempty list of enemy IDs
per wave. IDs must exist in the canonical enemy catalog and be unique within that
wave. List order is retained, including the initially selected target. Omitting
rosters retains the full catalog every wave, preserving existing recipes.

`examples/requests/create_outpost_encounters.json` demonstrates three initial
scouts, a heavier second encounter and the full final roster. Generate it using
`PYTHONPATH=src python -m axm_uc create examples/requests/create_outpost_encounters.json`.
Enemy scaling still derives from original values, never from damaged runtime
copies. All original arrival footprints stay reserved across waves.

Evidence: Python tests reject absent, empty, duplicate, unknown and malformed
rosters and verify normalized round-trips and caller-data independence. Node
executes the emitted wave operations to check order, scaling, independent enemy
copies, old-plan compatibility and bounds. The generator validates the complete
roster project. This pass changes generator source and adds a recipe; it does not
replace the published playtest or claim browser-observed encounter balance.
