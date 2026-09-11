# Visual State Compilation

AXM Universal Creation can treat visual prompt vocabulary as direction into a structured visual state space rather than as a bag of model-specific magic words.

This layer extends the existing `VISUAL_CREATION_GRAMMAR.md`. It does not replace that grammar or the procedural visual forge. The older grammar composes broad visual-intent axes and temporal beats. This atlas adds a more detailed, source-backed mapping for the 99 uploaded prompt terms, plus deterministic merge, conflict, and cross-media truth rules.

## Core model

A rendered frame can be treated as a projection of several related state layers:

`appearance state + scene state + projection state + temporal state + presentation state -> rendered observation`

The word **skin** can be useful shorthand for the visible result, but the machine keeps the layers separate:

- **appearance**: medium, aesthetic, surface material, palette, post-process, realism direction;
- **scene**: environment, genre, weather, visibility, time, illumination;
- **projection**: camera viewpoint, height, pitch, framing, lens, depth of field, output tier;
- **temporal**: motion, exposure accumulation, scale treatment, and later ordered state transitions;
- **format**: magazine, instant-film, or other presentation conventions.

All of these are represented as machine state. They are not separate substances inside the computer. The categories are inspectable handles that help humans and creation machinery modify the right relationships without losing meaning.

## Why prompt vocabulary transfers

An image prompt is not literal processor machine code. It can still carry information about:

- desired state;
- desired relationships;
- constraints;
- transition tendencies;
- evidence criteria.

For example:

`/3drender /isometric /miniature /goldenhour /rimlight`

can compile into state such as:

- three-dimensional render direction;
- isometric camera projection;
- miniature/diorama scale treatment;
- warm golden-hour scene time and illumination;
- rim-light contribution.

A learned image model may interpret those directions probabilistically. A deterministic machine can instead store them as explicit fields, map them to available render machinery, expose conflicts, and preserve what remains unknown.

The shared usefulness comes from the described state, not from the slash syntax and not from a claim that AI prompts are already executable CPU instructions.

## One state family, several media

The same visual-state description can inform several output families.

### Image

A still image needs:

- a subject representation;
- scene and appearance state;
- a camera/projection;
- a renderer;
- artifact-bound inspection.

The 99-command atlas can provide part of that state direction.

### Animation

Animation is not a different universe. It is state changing over time:

`state(t0) -> transition rule -> state(t1) -> ...`

The atlas can contribute appearance, camera, atmosphere, and exposure direction, but a real animation also needs:

- ordered target states or a timeline;
- motion paths;
- interpolation or simulation rules;
- rigging, deformation, particles, or frame-generation machinery where applicable;
- motion inspection against the actual artifact.

A static `/motionblur` token does not by itself define movement.

### 3D

A 3D scene is structured spatial state whose projection can produce one or many images. The atlas can contribute:

- camera direction;
- materials;
- lighting;
- environment;
- appearance and style;
- render-mode intention.

It does not uniquely recover:

- mesh geometry;
- topology;
- dimensions and coordinate relationships;
- rigging;
- collision;
- hidden surfaces;
- editable source.

Many different 3D scenes can produce nearly the same frame. The machine must preserve that ambiguity instead of pretending the visible skin uniquely specifies the body beneath it.

## Deterministic compilation

The runtime documents live under `src/axm_uc/data/visual_state/`.

The compiler performs:

1. validate the request;
2. extract slash commands or list aliases;
3. reject unknown aliases;
4. deduplicate and reorder by canonical source index;
5. validate every contributed state value;
6. merge contributions with path-specific, order-independent rules;
7. apply explicit schema-validated overrides;
8. evaluate known contradictions and tensions;
9. return a HOLD for unresolved hard conflicts;
10. derive renderer-neutral generator hints;
11. emit request, state, and compilation digests.

No input alias silently wins merely because it appeared last.

## Friction becomes path evidence

A contradiction such as:

`/topdown + /wormseyeview`

does not prove the requested visual direction is impossible. It proves that one single unscoped camera state cannot satisfy both descriptions at the same instant.

The caller may:

- use a camera sequence;
- declare separate named cameras;
- split subject and background layers;
- revise the direction.

This follows the current-boundary rule:

`current conflict -> expose missing scope/sequence decision -> retain target direction -> continue only when represented clearly`

The same principle applies to `/freezeaction + /motionblur`, `/sunrise + /sunset`, mixed art media, or fire underwater.

## Human table and machine specifications

`VISUAL_PROMPT_STATE_ATLAS.md` is the readable table.

The machine files are:

- `visual_prompt_aliases.json`: 99 aliases, provenance, mapping kind, state patch, overlap, and cautions;
- `visual_state_schema.json`: allowed state paths, types, ranges, and merge strategies;
- `visual_blend_rules.json`: deterministic merge behavior;
- `visual_conflicts.json`: HOLD and WARNING combinations;
- `visual_compiler_rules.json`: request contract, pipeline, and truth boundary.

## CLI

Show the compact atlas summary:

```bash
axm-assets state-catalog
```

Show all 99 normalized mappings:

```bash
axm-assets state-catalog --include-aliases
```

Compile an exact request:

```bash
axm-assets state-compile examples/visual-state-request.json
```

Python:

```python
from axm_uc.visual_state_prompt_atlas import compile_visual_state

result = compile_visual_state({
    "subject": "miniature robotic planet",
    "commands": "/3drender /isometric /miniature /goldenhour /rimlight",
})
```

Bridge:

```python
operate_visual_expansion(root, {
    "operation": "state-compile",
    "request": {
        "subject": "miniature robotic planet",
        "commands": ["/3drender", "/isometric", "/miniature"],
    },
})
```

## Source integrity

The source was a set of user-supplied reference images displaying “AI Prompts Compass.” The creator or owner and license were not otherwise supplied.

This repository does not copy the source thumbnails or poster graphics. It records the displayed source label, paraphrases the short descriptions, and transforms the vocabulary into a new structured state atlas.

The poster's marketing statement about unlimited visual possibilities is not used as technical evidence.

## Truth boundary

This lane establishes:

- a human-readable 99-command table;
- five machine-readable specifications;
- deterministic command extraction and compilation;
- schema validation;
- order-independent blending;
- explicit conflict handling;
- renderer-neutral cross-media requirements;
- CLI and bridge access.

It does not establish:

- that slash commands have universal meanings across image models;
- that compiled state is an image, animation, or 3D asset;
- that appearance uniquely determines hidden structure;
- that a generated artifact satisfies the intended style;
- automatic semantic extraction from arbitrary prose;
- automatic execution, installation, promotion, merge, or CANON authority.

The atlas is an extensible working representation. Artifact evidence may justify later refinement, splitting, merging, or replacement of mappings.
