# Deterministic Project Templates

`AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE` turns a reusable inspectable project recipe into a real UTF-8 software project.

A template contains:

- a nonempty `id` and `version`;
- a current project type: `generic`, `static-web`, or `python`;
- a mapping of relative file paths to exact template text;
- named placeholders written as `[[AXM:name]]`.

Variables may appear in paths and contents. Substitution is deliberately strict:

- every referenced variable must be supplied;
- unused supplied variables are rejected;
- malformed reserved placeholders are rejected;
- rendered path collisions and project-root escapes are rejected;
- values are inserted once as exact raw text;
- inserted values are not recursively expanded or semantically rewritten.

This is deterministic recipe instantiation, not a claim of semantic program synthesis. The caller or template owns grammar-specific escaping.

The resulting body uses the same grounded publication contract as direct project creation. Ordinary template creation retains observed gaps as a grounded draft; `publish_mode: "validated"` makes failed checks block publication.

The `self-candidate-project` handle can create inspectable source fragments, manifests, organs, or candidate projects for the machine itself outside the active body. For a complete independently buildable clone of the current machine, use `AXM-CAP-SELF-WORKSPACE` instead.

For a project composed from several independently identified template organs, use `AXM-CAP-ASSEMBLE-ORGAN-PROJECT`. It reuses this same renderer while adding dependency resolution and exact file ownership. See `ORGAN_ASSEMBLY.md`.
