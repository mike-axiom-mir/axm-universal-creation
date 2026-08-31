"""AXM Universal Creation runtime."""

__version__ = "0.1.0"


def _register_extension_builtins() -> None:
    """Register small runtime extensions without giving proposals self-authority."""
    from . import capabilities as _capabilities
    from .specialist_pool import operate_specialist_tournament

    def specialist_tournament(root, inputs):
        try:
            return operate_specialist_tournament(root, inputs)
        except (ValueError, TypeError) as exc:
            raise _capabilities.CapabilityError(str(exc)) from exc

    _capabilities.BUILTINS["builtin:specialist_tournament"] = specialist_tournament


_register_extension_builtins()
