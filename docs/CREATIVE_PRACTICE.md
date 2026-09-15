# Creative practice profiles

UC can now perform bounded creative practice through the actual recovered Studio
compositor, remember what happened, and use that evidence in the next session.
This is an opt-in workspace capability. It does not impose action logging on the
rest of UC, install a service, schedule background work or call a paid model.

## Use it

Python 3.11+ supplies SQLite; local Node.js runs the original Studio compositor.
Install UC with `python -m pip install .`. No npm packages are required.

```python
from axm_uc.creative_practice import Practice

with Practice('my-creation.sqlite') as practice:
    practice.profile('salvage', identity='my-maker', direction='free', seed=471,
                     intent='Explore readable playful materials')
    session = practice.start('salvage', project, source_root='source',
                             max_trials=12, active_seconds=120, checkpoint_every=4)
    result = practice.tick(session['id'])
    context = practice.context(session['id'])
    # Inspect the PNG via practice.artifact(result['png']) or export the trial.
    practice.export(session['id'], 'trial-preview', trial=result['id'])
    practice.review(result['id'], 'keep', actor='human:maker',
                    reason='This treatment fits the intended material')
    practice.control(session['id'], 'close')
```

`project` is an ordinary `axm.studio-composition-project/v1` with `recipe` and
`sources`; see [Studio donor](STUDIO_DONOR.md). Rendering failure returns a
`blocked` trial with its actual error; check `outcome` before using `png`.
Profile IDs are unique, explicitly named, and never guessed from an AI account.
Actor strings attribute feedback; they do not authenticate a caller or grant
special authority. Control of the database remains with its host.

The same methods are callable through JSON by humans, machines or an AI:

```sh
axm-practice my-creation.sqlite request.json
```

For example, `{"operation":"inventory"}` finds session IDs after restart.
`{"operation":"run","session":"SESSION_ID","ticks":6,"interval":5}` runs a
foreground heartbeat. Stopping the process stops the heartbeat. An existing host
heartbeat can instead call `tick` once at its own interval. No external task or
browser loop is necessary. Request paths are relative to the caller's working
directory. The CLI's `start` request embeds the Studio project as JSON.

| Operation | Purpose |
| --- | --- |
| `profile` | Create an identity-linked direction; optional `parent` snapshots its lessons |
| `start` | Capture an editable project and exact source PNG bytes into a session |
| `tick`, `run` | Execute one proposal or a bounded foreground series |
| `context`, `lessons`, `trial` | Retrieve bounded guidance and its full evidence |
| `review` | Keep/reject/uncertain with an attributed reason |
| `control` | Pause, resume or close; close seals a compact summary |
| `inventory`, `status`, `journal` | Find sessions and read checkpoints/paginated evidence |
| `export` | Replay-verify and publish an editable accepted revision or rendered trial |
| `backup` | Save one consistent portable SQLite cartridge, without overwrite |

## What actually learns

The deterministic starter repertoire contains six real operations: threshold,
posterization, pixelation, blur, sharpen and contrast. `graphic` and `surface`
select subsets; `free` explores both in seed-stable order. Existing layer filters
remain in place, and the first visible layer receives the experiment. This is a
small starter search, not an unlimited autonomous artist. Explicit layer-edit
proposals expose the compositor's full existing add/change/move/remove, blending,
filtering and mask controls; captured source assets remain fixed for the session.

Every attempt records its exact base, operations, engine fingerprint, output or
error, source references, review, and the lesson snapshot available before it.
Automatic selection queries **all matching prior observations** for that profile,
not just the last journal page, and skips already observed input/operation pairs.
A new session with the same input therefore makes a different choice. No-change
pixels and blocked operations remain useful observations. Repeated observations
are skipped unless explicitly retried; retries carry `repeat_of`, never a higher
confidence score. Identical feedback delivery retries return the existing judgment
without adding events or votes. An implementation change invalidates exact-match reuse.
A temporary runtime failure can be retried explicitly after repairing the runtime.

`context` returns current intent, project, capabilities and the latest 20 compact
observations/reviews. An optional AI or another proposer reads it and supplies:

```json
{"operation":"tick","session":"SESSION_ID","actor":"machine:proposer",
 "proposal":{"label":"soft paint",
 "operations":[{"op":"change","id":"paint",
 "patch":{"filters":[{"type":"blur","radius":1}]}}]}}
```

An AI integration must treat lesson text as data and guidance, not privileged
instructions. UC does not secretly invoke an AI or update model weights. Its
built-in selector learns which exact experiments have already been tried;
attributed judgment and richer composition come through the same explicit API.
Rendered/changed are technical observations, not automatic claims of quality.

Only explicit `keep` changes the session's working revision. Original source and
all attempts remain retained. A stale keep cannot overwrite a newer accepted
revision. Later dissent is appended and visible; rejecting a previously kept
trial does not silently undo it. Start from the retained original or another
export to take a different branch. `parent` copies lesson snapshots into a new
profile; future feedback/experiments in either profile do not alter the other.

## Journals without file proliferation

One SQLite database contains profile state, one logical journal per session,
trial evidence, compact summaries and content-addressed source/output blobs.
No per-tick files, per-lesson files, raw model thoughts, or idle heartbeat events.
Every completed attempt is transactional and immediately resumable. Periodic
checkpoints default to every four attempts; pause, review and close also seal a
checkpoint. Summary sealing does not delete underlying evidence.

Hard limits: 1 MiB per JSON record, 256 MiB per database, 128 trials and up to
3,600 active render seconds per session. Active time counts trial execution,
not sleep or the initial source capture. Time budgets stop the **next** trial;
an in-flight composition still has Studio's independent 30-second timeout.
`run` accepts at most 128 ticks and 0–60 seconds between ticks. Exhaustion pauses
once; idle calls after that write nothing. A full database causes transaction
rollback rather than silent evidence eviction. Back up/retain it and begin a
new cartridge when needed; no automatic deletion or cross-cartridge merge is
implemented. `backup` packages a consistent snapshot in one file.

SQLite serializes writers; a crashed attempt rolls back its metadata, blobs and
checkpoint together. An interrupted render can be recomputed on restart, but
cannot leave a committed success without its output. Avoid editing the database
through an unrelated SQL client while UC is using it. This is local persistence,
not cryptographic identity or a multi-host synchronization protocol.

## Evidence and boundaries

`python tools/creative_practice_proof.py OUTPUT` builds an original salvage paint
study. It exercises a real rejected filter, two memory-linked sessions, profile
forking, 1,000 idle ticks with no additional events, source-file loss, byte-exact
replay and a portable database copy. Dedicated CI runs the installed package
outside the repository and uploads the cartridge plus editable outputs.
Tests additionally kill a process mid-transaction, exercise stale reviews,
feedback isolation, repetition, bounded reads and source corruption.

The old Studio's heartbeat and `AXM.wisdom`/identity flow informed this adapter;
no donor source was modified or copied again. PR #76's session-curator Hand is
for evidence retention and exact temporary-capture cleanup, not a persistent
practice learner. It remains intact. Current integration executes **2D Studio
layer edits**. Other Hands, 3D/animation practice adapters and Studio profile UI
are subsequent connections. Missing-effect observations are evidence for a future
proposal, not automatic executable-organ installation. Existing root-fit and
self-change machinery stays authoritative for actual machinery changes.
