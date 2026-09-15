# Source-Bound Quest / Mission Flow Template Pack

`visual.mission.core` is the reusable mission/quest/reference foundation for games and interactive products.

Visual flow is never treated as runtime truth. A graph edge does not prove a branch is reachable; an objective card does not prove completion; a reward icon does not prove the reward exists or was granted.

## Surfaces

- project / mission hub
- objective editor
- prerequisite / condition editor
- branch / flow graph
- world / map binding editor
- rewards / outcomes editor
- failure / retry / recovery editor
- runtime-state / flag inspector
- mission variant editor
- review / export

## Source-truth contract

- `mission-source` — exact mission identity, source, version, digest and owning context;
- `objective-state` — exact objective ID/type/status/completion source;
- `mission-condition` — exact subject/operator/value/source and evaluation state;
- `mission-edge` — exact from/to identities, transition type and condition references;
- `mission-world-reference` — exact map/zone/POI/entity target plus source/status;
- `mission-reward-reference` — exact reward/outcome identity, source, amount/state and delivery status;
- `mission-failure-recovery` — exact failure condition, retry/recovery/checkpoint destination and consequences;
- `mission-runtime-flag` — exact flag ID/value/source/freshness;
- `mission-variant` — exact base mission, deltas, context and availability;
- `mission-export-target` — exact objective/condition/branch/reference/reward/recovery requirements.

## Truth boundary

Map proximity does not create a mission binding. Branch lines do not establish reachability. Objective completion requires observed state. Reward presentation is not delivery evidence. Failure/retry/recovery consequences stay explicit.

This pack proves deterministic structural/editability contracts only. It does not prove mission balance, narrative quality, branch reachability under a real runtime, reward correctness, map correctness or gameplay acceptance.