# Grammar 102 and Grammar Glass workbench

Universal Creation now carries the upstream Grammar 102 standalone capability
package and selected Grammar Glass state/render modules. Python and Node.js are
required; no npm install, network service, donor checkout or model is required
at runtime. The adapters consume explicit JSON, not a caller workspace scan.

```bash
PYTHONPATH=src python -m axm_uc grammar-capsule examples/grammar/rust.json
PYTHONPATH=src python -m axm_uc state-ripple examples/grammar/ripple.json
```

`grammar-capsule` returns the real upstream language resolution, organ/grammar
plans, specialist review, template capsules, keyboard layout, cheatcode/influence
suggestions and optional direction gaps. This is a read-only advisory capsule:
it does not generate a complete app, run a compiler or prove that all 102
languages have executable toolchains. Conflicting language/path signals remain
held. Existing UC direction catalogs are not silently replaced.

`state-ripple` takes `fabric`, `initialState`, `changedState` and optional
`wakeBudget`. It evaluates the baseline, performs a sparse update and compares
it with a full recalculation in the same process. The example changes ore while
food stays unchanged: two nodes execute, one is reused, and both paths return a
total of 10. Operations are the donor's closed state-operation language, not
arbitrary JavaScript or shell execution. The comparison deliberately runs the
full path too; it is an equivalence check, not a wall-clock acceleration claim.
The vendored JS API also exposes `runAll`, `sparseUpdate` and baseline validation
for callers maintaining a longer-lived explicit state graph. It is not wired
into existing game loops automatically.

`render-budget REQUEST.json` accepts `atoms` and optional `mode` (AUTO, SAFE,
BALANCED, FULL). SAFE selects up to 384, BALANCED up to 768; FULL retains all.
AUTO uses SAFE above 800 atoms, otherwise FULL. Selection balances recorded
language groups and returns the selected entries plus counts omitted from the
projection. Original input state is not changed. This creates a selection plan;
it does not draw it or measure frame rate. Input is capped at 10,000 atoms.

All three commands accept at most 1 MiB of JSON, reject non-finite Python inputs,
and stop subprocess work after 30 seconds. Grammar 102's pinned source archive
is hash-checked, extracted as ordinary files into a temporary directory, executed
through its supplied stdin CLI and removed afterwards. No installation hooks or
package-manager operation runs at invocation. The packed source remains readable
by extracting `third_party/grammar-workbench/grammar-102.tgz`.

## Provenance and evidence

Grammar 102: `ff58375b65a4033041e6de957263d4146aa7429e`.
The 1.1 MB compressed archive is produced by the upstream `npm pack --ignore-scripts`
allowlist (approximately 14.8 MB unpacked). It contains the actual 102-language
package, not a source redirect. Its license is included inside the package.

Grammar Glass: `e046b7adb5873b666c79182c90d46438116eef03`.
State Ripple, Construction Program, Playground and Render Budget modules and
four focused regression suites are copied byte for byte. Apache-2.0 license and
individual digests are retained in `third_party/grammar-workbench/`.
The process adapter and request examples are local UC code.

The upstream large-graph regression passes: 1,001 nodes in the initial full run;
a single input mutation executes 11 nodes and reuses 990, with sparse/full
comparison evidence. Additional regressions cover invalid state and tampered
baseline admission. UC integration checks exercise the packaged Rust capsule,
repeatability and conflicting language holds, the three-node update example,
and a 1,000-atom projection. No browser rendering or measured FPS claim is made.

Larger donor features remain separate: workspace edit/recovery hands, polyglot
minimal reverification, Construction Hand candidate generation, and discovery
ledger recovery have not been installed by this pass. Their presence upstream
does not imply Universal Creation can already invoke them.

## Construction programs

`PYTHONPATH=src python -m axm_uc construction-program examples/grammar/construction.json`

Compose up to 12 modules / 128 operations using the pinned Glass construction
core already included in this workbench. Operations are SET, INCREMENT,
TRANSITION, ASSERT_EQ and EMIT_SIGNAL. Each module declares reads, writes,
dependencies and signals. Unordered overlapping writes and dependency cycles
are rejected. The command returns the normalized program and its digest.

Set `execute: true` to evaluate against an `initialState` JSON object; otherwise
execution is null. The example supplies an outpost, spends four supplies on a
turret, checks that it exists, and enters the defend phase. This constructs and
runs a bounded state program, not HTML or arbitrary source code. It does not
connect itself to existing games.

Changes are atomic per module: a failing assertion discards that module's staged
changes and stops later modules. Previously successful modules remain committed
in the returned state. This is not whole-program rollback or crash recovery.
The input object is unchanged; output is returned on stdout, with no project write.

### Recovery integration assessment

Grammar 102's `workspace-edit-hand.js` and `workspace-edit-journal.js` include
real target-file replacement, external journal storage, leases, recovery, and
parser-process bindings. They are not exposed by this adapter. Integrating them
requires connecting their exact-target and journal contracts to UC workspace
isolation and exercising interrupted-write recovery. A transient state rollback
test is not evidence of durable file recovery.
