# Professional crews inside Universal Creation

UC can now carry a local crew across jobs. Its members use pinned Profession
Fabric bodies, procedures, failure libraries and handoff contracts. A job binds
each explicit station to a profession, a body skill and an existing UC tool.

The first bundle contains 18 existing professions. No new profession was needed.
Work-type recipes cover software, web, 3D, animation, games, audio and documents.
These are ownership and consultation maps: automatic execution currently covers
text/JSON, basic text projects, project verification and bounded procedural GLB.
Other stations report a capability gap. A `judgment: "REQUIRED"` station stops
before execution and identifies its owner; it cannot invent approval.

## What actually learns

The local crew remembers distinct observed successes, failures and failed check
types, scoped to the profession, skill, action kind, project type, explicit
context, provider source revision and profession catalog. After a project
failure, the next matching job performs a temporary build and validation before
writing the requested target. A repeated defect stops at that learned preflight;
corrected input can pass it. Planning and specialist packets expose that memory.

This is deterministic adaptation through experience. It is not neural training,
autonomous professional reasoning, a points system or evidence of artistic
mastery. Repeating identical work under new run IDs does not add new experience.
Source/context changes invalidate transfer without deleting the older practice.

Jobs and compact practice live in `state/profession-crews/<crew_id>.json`.
The normal UC snapshot/recovery mechanism covers this state. No simulator reward
system, immutable root hash protocol or mandatory global action ledger is added.
Crews are local, offline, optional and independent. No cloud account/model is
needed. At 256 retained jobs the crew holds and asks for a new identifier after
preserving/exporting the old state; it does not silently discard history.

## Run a job

From the repository root:

```sh
python -m axm_uc.cli create examples/profession-crew-python.json
python -m axm_uc.cli create examples/profession-crew-verify.json
python tools/profession_crew_demo.py
```

For a source checkout without installation, prefix Python commands with
`PYTHONPATH=src` on POSIX, or install the project in your usual local environment.
The demo uses a temporary machine state and shows an actual failure -> remembered
preflight -> corrected job -> fresh verification sequence. It does not alter the
repository's crew state.

Supported operations through `kind: "profession-crew"` (alias
`profession-workflow`) are `catalog`, `inspect`, `plan`, `run`, `verify` and
`prepare-specialists`. Planning is read-only. `run` executes the caller's explicit
stations, observes the real artifacts, and updates only that crew's local memory.
`verify` reopens artifacts, checks their exact identity and checks runtime/catalog
freshness. Previously completed output is not assumed current.

Each station accepts `id`, `profession_id`, `skill_id`, `purpose`, `action`,
`depends_on`, and `judgment`. Missing profession/skill selections use the declared
work-type lead and its first skill; this is visible in the plan, not evidence
that the tool operation demonstrates the whole skill. Dependencies must name
earlier stations. Failed checks stop later stations. Automatic stations cannot
write UC's protected machine body. A job interrupted between writes is retained
as interrupted and cannot silently execute again under the same run ID.

## Existing specialist workflow connection

Call `prepare-specialists` on a professional job, or pass the job as
`profession_workflow` to the existing `specialist-tournament` `prepare` operation:

```json
{
  "kind": "specialist-tournament",
  "inputs": {
    "operation": "prepare",
    "profession_workflow": {
      "crew_id": "asset-team",
      "work_type": "3d",
      "goal": "Assess an explicit asset build and its missing evidence",
      "steps": [{
        "id": "render-review",
        "profession_id": "art-director",
        "judgment": "REQUIRED",
        "action": {"kind": "render-quality-review", "inputs": {}}
      }]
    },
    "pool_size": 20,
    "max_teams": 8
  }
}
```

The existing tournament keeps its specialist identities, team construction,
ranking and evidence boundary. Each team receives professional contracts,
procedures, handoffs, provenance and relevant crew practice. Its result retains
the original tournament schema and can use the existing judging API. Packets
are prepared work, not a claim that agents have run. Tournament votes do not
change professional memory or maturity.

The plan also exports the existing `stepwise_plan` contract. This lets a human,
cognition provider or existing stepwise executor handle judgment-heavy work
without a second set of step semantics. Direct crew execution only handles the
registered deterministic artifact observers.

## Evidence ceilings and next adapters

- All imported professions remain **EXPERIMENTAL**.
- `COMPLETE_BOUNDED_CHECKS` means the selected automatic stations completed and
  their bounded artifact checks passed. It does not mean professional acceptance.
- GLB checks bind the emitted file to the requested specification and inspect
  container/geometry; they do not claim good art, motion or engine compatibility.
- Software checks do not execute the generated software or prove usability.
- Automatic audio, animation, rendered comparison and interactive playtest
  adapters are still gaps. The workflow/ownership maps are present; those
  execution/evidence adapters must be added with real fixtures.
- Learning changes preflight behavior; it does not silently edit source bodies,
  accepted creative intent, roots, user files, team votes or upstream professions.

## Source continuity

Professional data is copied as JSON values from
`mike-axiom-mir/axm-profession-fabric` at
`941bd05007eb5cd88e773e66c858c62cf9de38a9`. The catalog preserves original body,
workflow/procedure/failure/handoff values, exact source paths and source-byte
hashes. The Apache-2.0 license and notice are bundled with package data.

The design was informed by `axm-factual-space-simulator` at
`dd3b2b6d773151573a2b305a4858ea7f87408f78`, especially
`src/axm_star_sim/crew_station_metrics.py` and `rooted_crew.py`. Its useful pattern
is role -> observed situation -> specific skill evidence -> changed next action.
No simulator code or its reward/promotion/ledger machinery was copied into UC.

This lane extends UC main `49ef11ca42b2079dffbd595daa8ea8626b99d2ab` and preserves
the separate aftertouch and physics lanes. It does not claim those PRs are merged.
