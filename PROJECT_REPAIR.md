# AXM Universal Creation — Persistent Project Repair

Universal Creation can now repair an existing text project without regenerating the complete creation body.

The current repair route is deliberately deterministic and explicit:

`existing project -> stage copy -> explicit operations -> deterministic validation -> transactional publish -> independent verification`

## Operations

`AXM-CAP-PATCH-PROJECT` accepts a non-empty `operations` list with four operations:

- `add`: add one new UTF-8 text file; fails if the target already exists;
- `update`: replace the exact text of one existing file; fails if the file does not exist;
- `delete`: remove one existing file;
- `rename`: move one existing file to a new project-relative path; fails if the destination already exists.

Every operation path must remain inside the project body.

Unmentioned files are copied forward unchanged.

## Transactional repair

Repair never edits the live project in place.

1. The existing project is copied to a temporary repair body.
2. Operations are applied to that body.
3. Deterministic validation runs against the staged body.
4. If validation fails, the original project is untouched.
5. If validation passes, the staged project is published while the prior project remains available as rollback material.
6. Validation runs again against the published project.
7. Only after post-publish validation passes is the prior project removed.

The result separates:

- `intent`: the normalized operations supplied for this repair;
- `observed`: the operations actually applied plus before/after file manifests;
- `expected_files`: exact changed-file text carried forward for independent verification;
- `validation`: deterministic checks on the resulting project;
- `grammar_inventory`: current locally recognized file grammars and the actual strength of validation available for each.

This is current-state evidence from one repair invocation, not an activity-history subsystem.

## Verified repair composite

`AXM-CAP-VERIFIED-PROJECT-REPAIR` is a manifest-only `DETERMINISTIC_COMPOSITE`:

`PATCH-PROJECT -> VERIFY-PROJECT`

The second step receives the exact changed-file expectations observed by the patch step, so a caller does not need to resend the entire project merely to verify a small repair.

Current handles:

- `verified-project-repair`
- `verified-static-web-repair`
- `verified-python-repair`

## Grammar awareness

This run borrows a useful structural idea from `axm-102-grammer`: make grammar identity and validation strength explicit instead of collapsing them into a vague claim that code is valid.

Universal Creation does **not** import the donor repository's learning ledgers or claim to contain its full grammar corpus.

The current small local inventory recognizes:

| Extension | Grammar | Current validation truth |
| --- | --- | --- |
| `.py` | Python | parser-backed through Python compile validation |
| `.json` | JSON | parser-backed automatic `json-valid` check |
| `.html`, `.htm` | HTML | local-reference structural validation, not complete HTML validity |
| `.js`, `.mjs` | JavaScript | identified only; no current parser validation |
| `.css` | CSS | identified only; no current parser validation |
| `.md` | Markdown | identified only; no current parser validation |
| `.txt` | plain text | text only |

That distinction matters. Recognizing `.js` is not permission to claim its syntax or behavior was verified.

`axm-grammer-glass` remains useful donor material for a later cross-grammar relation/composition run. The published `axm-walmi` repository was inspected for a directly reusable repair primitive, but none was imported into this narrow repair path.

## Anatomy

The live patch capability explicitly implements:

`AXM-05-CODE-GRAMMAR-C-029-code-patch`

with a bounded meaning: exact text-project add/update/delete/rename operations plus staged deterministic validation. It does **not** claim semantic AST-level patching.

The verified repair composite only declares that it **uses** that component and the existing project/validation components. It does not falsely count the composition as another implementation of the same anatomy.

## Try it

Create the existing example first:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/create_verified_site.json
```

Then repair it:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/repair_verified_site.json
```

The repair updates `index.html` and adds `repair-note.md`. Existing `style.css` and `app.js` are carried forward rather than regenerated.

## Current boundary

This milestone does not yet perform AST-aware edits, source-range edits, automatic diagnosis-to-patch generation, generated-code execution, or browser visual/interaction verification.

Those are future capability gaps, not hidden features.
