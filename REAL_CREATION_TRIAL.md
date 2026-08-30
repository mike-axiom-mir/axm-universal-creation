# AXM Universal Creation — Real Creation Trial

This is the handoff point for a working AI chat or local operator to try a real creation without pretending the machine is already universal.

## What is real at this milestone

AXM Universal Creation can now:

1. decompose a structured creation request against the explicit 2,165-record anatomy;
2. show relevant atoms, components, organs, dependency hints, and live capability coverage;
3. create a multi-file UTF-8 project body through an inspectable deterministic capability;
4. stage and validate that project before publishing it;
5. independently re-open and verify the published project;
6. return a single `CREATION_TRIAL` result containing the plan, creation result, verification result, and pass/fail state.

The current project validator supports:

- `file-exists`
- `nonempty`
- `contains`
- `json-valid`
- `python-compile`
- `html-local-links`

`static-web` projects automatically require `index.html` and verify local `src`/`href` references from every `.html` and `.htm` page in the project.

`python` projects automatically compile every `.py` file for syntax without executing the generated program.

Every `.json` file is automatically parsed for JSON validity in every project type.

## Important truth boundary

A passing deterministic project trial means:

- the requested files were actually written;
- project-relative paths stayed inside the project body;
- configured deterministic checks passed;
- every JSON file parsed successfully;
- local static-web references in every HTML/HTM page resolved when that project type was used;
- Python source parsed/compiled when that project type was used;
- the published project matched what the verifier subsequently observed.

It does **not** mean:

- generated code was executed;
- browser interaction was automatically proven;
- visual quality was automatically judged;
- the creation is universally correct;
- every user requirement was semantically satisfied.

Those are later/host/user/model tests, and should be reported as such rather than silently promoted to truth.

## First included trial

Run:

```bash
PYTHONPATH=src python -m axm_uc plan examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc trial examples/requests/create_real_site.json
PYTHONPATH=src python -m axm_uc create examples/requests/verify_real_site.json
```

The trial writes:

```text
creations/first-real-site/
  index.html
  style.css
  app.js
```

Open `creations/first-real-site/index.html` in a browser for the human/host-side visual and interaction test.

## Working-chat protocol

A working AI chat should not rewrite the machine architecture just to make a creation.

For an ordinary first trial:

1. translate the user's requested outcome into one structured request;
2. choose `static-web-project`, `python-project`, or `software-project` when the current project builder is sufficient;
3. put exact proposed file contents under `inputs.files`;
4. add deterministic checks that reflect claims the chat intends to make;
5. run `axm-uc trial`;
6. inspect the returned plan, creation result, verifier result, and limitations;
7. only claim what was actually tested;
8. if the current capability is insufficient, preserve the returned gap instead of hiding it with prose.

This is intentionally a narrow first creation body. Binary assets, media generation, browser automation, code execution, packaging, and broader creation organs can be added as real gaps are encountered.
