# AXM Platform Hands capsule

Exact portable intake of the AXM Collaboration Platform's modular executable Hands at the pinned donor revision in `INTAKE_RECEIPT.json`.

## Families

- `shared/asset-hands/` — host-callable creation, edit, inspection, validation, finishing and workflow capabilities.
- `shared/ai-native-hands/` — bounded executable mechanics for AI-native skills (evidence routing, capability-gap checks, curation, ephemeral vision, computed-style inspection and native-eye fallback).

The copied support files preserve the donor-relative runtime paths without importing the whole Collaboration Platform.

## Universal Creation use

`require('./capabilities/platform-hands')` from the repository root. Universal Creation may route suitable creation requests to `assetHands` and may use `aiNativeHands` for bounded evidence/capability mechanics. The Hands remain capability modules: importing them does not grant permissions, publish results, promote canon or turn an AI skill into authority.

This is an intake copy, not a new canonical source. Improvements should remain explicit and provenance-bound until a shared-package/update route is chosen.
