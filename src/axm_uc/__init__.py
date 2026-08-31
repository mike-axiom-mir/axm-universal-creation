"""AXM Universal Creation runtime."""

__version__ = "0.1.0"


def _register_extension_builtins() -> None:
    """Register small runtime extensions without giving proposals self-authority."""
    from . import capabilities as _capabilities
    from . import specialist_pool as _specialist_pool
    from .specialist_pool_extension import build_specialist_pool as _contextual_pool_builder

    # The universal body contains twenty reusable lenses. Allow up to twenty
    # challenge-derived registry specialists so the declared 40-person maximum
    # can actually be reached when enough exact registry matches exist.
    _specialist_pool.MAX_DERIVED_SPECIALISTS = 20

    # Keep challenge-context detection independent of how many specialist
    # profiles the caller chooses to display. Small pools may remain universal,
    # while contextual +1 history still binds to the actual matched domains.
    _specialist_pool.build_specialist_pool = _contextual_pool_builder

    def specialist_tournament(root, inputs):
        try:
            return _specialist_pool.operate_specialist_tournament(root, inputs)
        except (ValueError, TypeError) as exc:
            raise _capabilities.CapabilityError(str(exc)) from exc

    _capabilities.BUILTINS["builtin:specialist_tournament"] = specialist_tournament


_register_extension_builtins()
