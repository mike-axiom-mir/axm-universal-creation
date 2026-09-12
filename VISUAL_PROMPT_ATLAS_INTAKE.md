# Applying the supplied Global Visual Prompt Atlas research to UC

This note records a design proposal supplied by the user on 2026-09-12.
The pasted citation tokens did not include resolvable source URLs. Its current
platform versions, counts, access terms and legal claims were not independently
verified in this pass and are not adopted as machine facts.

UC's existing `visual_state_prompt_atlas.py` compiles known command aliases into
renderer-neutral visual state. It is not a global prompt-occurrence index. The
Design Fabric source lens, visual-state compiler and artifact-bound review
machinery should remain in place. A source-intake layer can feed them without
replacing their working contracts.

## Useful additions

| Research idea | Fit inside Universal Creation |
| --- | --- |
| Separate prompt content from its occurrences | One exact content record can have multiple attributed observations; retain each source instead of deleting duplicates |
| Separate intent from execution | Positive/negative/edit instructions and reference roles remain distinct from seed, model, sampler and other generation settings |
| Preserve original and derived representations | Retain exact supplied text/bytes; normalization, translation, tags and compiled visual state are separate attributed outputs |
| Treat references as typed inputs | Style, subject, mask, depth, pose and layout carry explicit roles; recording a role does not establish that a renderer supports it |
| Preserve workflow and event lineage | Link a recipe, its invocation, output hashes and reviews; equal prompts do not imply equal executions |
| Retain unknown rights and quality | No license, successful render, semantic equivalence or artistic quality is inferred from public visibility or metadata completeness |
| Reversible similarity relationships | Suggest near-duplicate/translation/template links without silently merging originals |

For current game-asset creation this would let a brief preserve, for example:
survivor faction identity, a silhouette reference, material references, output
scale, preservation constraints, and the specific geometry recipe selected.
Each adapter should expose which requirements it realizes and which remain
unresolved. A unsupported pose or depth reference must remain visible rather
than disappearing when the recipe is compiled.

## First bounded implementation to build

An offline importer for explicitly supplied JSON/JSONL records, integrated with
UC's existing transactional project output. It should require no crawler,
database server, embeddings service or model.

1. Validate a versioned record with exact original text, source occurrence,
   caller-supplied provenance, typed references and separate execution settings.
2. Use structured, versioned hash inputs so field boundaries are unambiguous.
   Preserve Unicode and whitespace in original identity. A normalized comparison
   key may link candidates, but must not equate case, reference order, weighting
   syntax or invisible characters without evidence that they are nonsemantic.
3. Retain all occurrences while deduplicating exact content records. Equal
   configuration means a configuration match, not proof of the same real event.
4. Keep claimed source URLs, dates, licenses and observer identities attributed
   as supplied metadata. Do not fetch references or certify rights implicitly.
5. Allow an explicit adapter to compile supported local visual commands. Report
   unsupported conditioning fields; bind derived output to the input digest.
6. Export original records, relationships and an inspectable manifest together.

Acceptance examples: identical content from two sources retains two occurrences;
changed seed retains content identity but changes execution configuration;
changed reference order changes conditioning identity; normalization never
rewrites the original; unknown rights remain unknown; prompt text never executes;
invalid input leaves the previous project untouched.

This intake implementation is a next step, not installed by this note. No global
crawl, paid prompt collection, social-platform connector, automatic translation,
embedding index or imported public corpus was added. Acquisition should be
scoped separately to actual sources and applicable access/retention permission.
The research's scale estimates are planning ideas, not targets for UC growth.

## Root fit

Truth: preserve source versus interpretation and capability versus declaration.
Agency: explicit intake and export choices; supplied prompts cannot command the
importer or gain permissions. Continuity: keep originals, source lineage and
versioned derivatives. Wisdom before speed: prove a small useful creation path
before expanding collection scale. Internal merge review follows these roots;
founder identity is not the constitutional gate.
