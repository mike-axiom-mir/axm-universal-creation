# Material donor invariant receipt v1

## Status

**Executable donor-owned evidence surface / bounded probe / not CANON.**

`tools/material_donor_invariant_receipt.py` executes the existing material donor adapter against one retained self-made probe fixture and emits a deterministic JSON receipt for cross-repository verification.

It does not replace `adapt_material_donor_pack`, change donor semantics, or grant authority to a consumer.

## Why this exists

A consumer should not have to hand-rewrite Universal Creation's material donor behavior in order to observe whether the adapter still:

- preserves declared pack/library/entry identity on a complete adaptation;
- leaves an unassigned channel visibly held and rejects it in strict mode;
- keeps accepted texture entries while holding a family with duplicate channel bindings;
- rejects an unsupported donor version;
- keeps rendering unverified.

The receipt is produced by executing the donor-owned adapter itself. It therefore gives consumers a bounded runtime observation without pretending to prove arbitrary donor packs or image/material semantics.

## Run

```bash
python tools/material_donor_invariant_receipt.py
```

The default fixture is `fixtures/material-donor-invariant-probe-v1.json`.

## Truth boundary

The receipt proves only the exact executed adapter behavior over that fixture and its three deterministic mutations. It does **not** prove authorship, real image semantics, PBR correctness, rendering, deployment, arbitrary material packs, or constitutional/CANON authority.

All emitted authority fields are false. Consumers may verify or hold on this evidence, but the receipt cannot execute, merge, promote, or declare CANON.
