# Shared Gameplay Visual Template Pack

`game.shared.core` fills reusable gameplay-system gaps that are likely to recur across AXM games without duplicating the already-merged account/settings/network shell.

## Surfaces

The product contains twelve responsive screens:

- inventory / equipment;
- skill and upgrade tree;
- mission briefing;
- world / mission map;
- objective / quest log;
- upgrade shop;
- codex / lore;
- revive overlay;
- boss encounter HUD;
- spectator / follow view;
- end-session summary;
- challenge / goals board.

## State-aware primitives

The pack adds reusable contracts rather than only layout rectangles:

- `inventory-slot` — ownership, quantity/equipped/compatibility state;
- `skill-node` — prerequisites, cost and unlock state;
- `objective-row` — explicit objective lifecycle and progress;
- `shop-offer` — exact cost and result/ownership state;
- `codex-entry` — discovered vs unknown knowledge;
- `revive-state` — downed/revive actor/time state;
- `boss-phase` — encounter phase/vulnerability cues;
- `spectator-seat` — viewed target and control context;
- `challenge-card` — goal, progress, expiry and reward;
- `session-stat` — post-session metric with personal/team scope.

## Visual language

`game.shared.adventure` is a neutral high-readability game-system style intended to be overridden by a specific game's identity while retaining the structural contracts.

## Truth boundary

The pack proves deterministic responsive structure and explicit state vocabulary. It does not prove gameplay balance, economy tuning, progression fairness, encounter timing, revive mechanics, item compatibility logic or actual runtime state. Real games must bind these surfaces to their own observed systems.
