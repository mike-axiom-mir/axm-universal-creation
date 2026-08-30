# Grounded Creation

Grounded creation is not guarded output.

The ordinary creation path is allowed to retain an imperfect result. Deterministic checks describe what is currently true about that creation; they do not automatically erase the creation because a gap exists.

The current project capability therefore has two explicit publication modes:

- `grounded-draft` is the default for ordinary creation. Exact requested text must be published intact, but failed JSON, Python, HTML-reference, or caller-supplied checks remain attached as visible gaps and the draft survives.
- `validated` is an explicitly strict route. Any failed deterministic check prevents publication or restores the previous project body.

Publication integrity is required in both modes: the project must be nonempty, paths must remain inside the project, and the published files must exactly match the supplied text. This is not a quality gate; it is the minimum truth needed to say that the machine created the body it was asked to create.

Verified composite handles use `validated` mode. Plain `software-project`, `static-web-project`, and `python-project` handles use `grounded-draft` unless the caller asks otherwise.

The returned grounding receipt separates:

- whether the body was retained;
- whether validation passed;
- whether the creation is a `VALIDATED_CREATION` or `GROUNDED_DRAFT`;
- the exact observed checks that did not pass.

This lets creation and real use expose capability gaps without turning those gaps into hidden claims or automatic prohibitions.
