# Design Fabric Rendered Observer Loop

Design Fabric v0.3 closes another part of the gap between **design source** and **rendered evidence** without pretending those are the same thing.

The connected loop is now:

`Design Genome -> design plan -> optional local browser capture -> render observation -> integrated judgment -> repair direction -> explicit repair -> render again`

This stays inside `AXM-CAP-DESIGN-FABRIC`. It is an observer/evidence layer, not a second design ontology or another general creation machine.

## 1. Render observation contract

Schema:

`axm.design-render-observation/v0.1`

Every observation is bound to one exact `plan_digest` and one attributed observer.

Supported observer kinds are:

- `human`;
- `browser-tool`;
- `model`;
- `test-fixture`;
- `other`.

A receipt may contain one capture per requested viewport. Each capture keeps:

- exact viewport id and dimensions;
- artifact digests and byte-evidence status;
- deterministic measurements when supplied;
- attributed perceptual assessments when supplied;
- one deterministic capture digest.

Artifact kinds include screenshots, DOM snapshots, accessibility trees, interaction logs, computed styles, performance traces, and openly labeled other artifacts.

For ordinary externally supplied observations, a SHA-256 value remains a **declared digest**. Design Fabric does not silently claim it fetched or verified those bytes.

## 2. Local browser bridge

v0.3 adds an optional local executor:

`capture-design-browser-observation` -> `capture-browser`

Schema:

`axm.design-browser-capture-receipt/v0.1`

The caller explicitly supplies:

- a local HTML file or directory containing `index.html`;
- the exact Design Plan;
- the exact width/height for every viewport declared by that plan;
- a caller-selected Chromium-compatible executable path or explicit executable name on `PATH`;
- a new output directory;
- an optional bounded timeout.

The bridge does **not** install, download, or discover a browser by itself.

For each viewport it invokes the selected executable in headless mode and requests:

- a PNG screenshot;
- a DOM dump.

The bridge then reads the bytes that were actually produced, computes their SHA-256 digests, records browser path/version and target HTML digest, and materializes:

```text
capture/
├── browser.capture.json
├── mobile.png
├── mobile.dom.html
├── desktop.png
└── desktop.dom.html
```

The actual file names follow the declared viewport ids.

### Local/offline boundary

The bridge accepts local HTML paths only. URL targets are rejected.

Its Chromium command disables background networking and maps external host resolution away from normal resolution. This is an explicit **host-resolution block**, not a claim of a complete operating-system network sandbox. Direct browser behavior remains part of the selected executable's runtime boundary.

Local page JavaScript may execute inside that browser. The browser executable and version are therefore retained as provenance.

### Evidence distinction

Browser-produced screenshot/DOM bytes are marked:

`bytes_verified_or_fetched_by_design_fabric: true`

Merely supplied external artifact claims remain false.

That gives the evidence system a clean distinction between:

`someone says this digest describes an artifact`

and

`this bridge actually received these bytes and hashed them`.

## 3. Runtime measurements

The observation contract can carry bounded measurements for:

- horizontal overflow;
- visible focus behavior;
- reduced-motion behavior;
- minimum rendered text contrast;
- interaction error count.

The current v0.3 browser bridge does **not yet derive those measurements automatically**. A successful screenshot/DOM capture therefore does not automatically become a visual-quality PASS.

When the measurements are missing, the integrated judge keeps the corresponding gates on `HOLD`.

## 4. Perceptual assessments

Visual qualities that cannot be reduced to deterministic measurements stay attributed assessments rather than being promoted to objective facts.

The default integrated judgment requests:

- `visual-hierarchy`;
- `spacing-consistency`;
- `component-coherence`.

Each assessment carries:

- `PASS`, `FAIL`, or `HOLD`;
- confidence from `0..1`;
- an explicit basis;
- observer identity through the observation receipt.

A vision model, human reviewer, or other authorized observer can therefore contribute visual judgment without becoming hidden authority inside the Design Genome.

## 5. Integrated judgment

Schema:

`axm.design-integrated-judgment/v0.1`

The integrated judge combines the structural Design Judge with render-evidence gates for:

- requested viewport coverage;
- screenshot evidence coverage;
- horizontal overflow;
- runtime focus visibility;
- runtime reduced-motion behavior;
- rendered text contrast;
- interaction errors;
- required perceptual assessments.

The status rule is:

`any FAIL -> FAIL`

`otherwise any HOLD -> HOLD`

`otherwise -> PASS`

A PASS is narrow evidence for one exact plan and observation set. It is not a universal claim of beauty, originality, accessibility, or correctness.

## 6. Repair direction

Schema:

`axm.design-repair-plan/v0.1`

A failed or held integrated judgment can produce deterministic repair direction such as:

- responsive-layout repair;
- interaction-state repair;
- motion-policy repair;
- color-system repair;
- interaction-runtime repair;
- visual-composition repair;
- missing observer evidence.

This repair plan does not modify source by itself and cannot accept its own repair.

The intended connection remains existing Universal Creation repair machinery:

`repair direction -> explicit bounded source patch -> existing verification -> browser render -> fresh observation`

That preserves the separation between **evidence**, **proposed change**, **execution**, and **acceptance**.

## Live operations

| Creation kind | Operation | Result |
| --- | --- | --- |
| `inspect-design-observer` | `inspect-observer` | Inspect observer schemas and truth boundaries. |
| `record-design-render-observation` | `record-render-observation` | Normalize and digest attributed viewport evidence. |
| `capture-design-browser-observation` | `capture-browser` | Use an explicitly supplied local Chromium-compatible executable to capture screenshot + DOM bytes. |
| `judge-rendered-design` | `judge-rendered` | Combine structural and render evidence. |
| `propose-design-repair` | `propose-repair` | Convert failed/held gates into bounded repair direction. |

## What remains

The machine now has a **camera socket and an optional local camera executor**, but not the whole visual nervous system yet.

The next useful browser growth is to extract real runtime evidence from the rendered page:

1. computed geometry and overflow;
2. focus state and keyboard navigation evidence;
3. reduced-motion behavior;
4. accessibility-tree evidence;
5. rendered foreground/background contrast observations;
6. bounded interaction execution and runtime errors.

A separate vision observer can then inspect the captured screenshots for hierarchy, spacing, coherence, and other perceptual qualities while keeping model/version/source receipts.

The target loop becomes:

`create -> real browser capture -> deterministic runtime evidence + attributed visual observation -> judge -> bounded repair -> re-render -> compare`

The important part is unchanged: missing eyes produce `HOLD`, not invented sight.
