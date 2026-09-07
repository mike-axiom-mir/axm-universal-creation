"""AXM Universal Creation runtime."""

__version__ = "0.1.0"


def _register_extension_builtins() -> None:
    """Register small runtime extensions without giving proposals self-authority."""
    from . import capabilities as _capabilities
    from . import specialist_pool as _specialist_pool
    from .chameleon import ChameleonError, operate_chameleon
    from .design_browser import DesignBrowserError, operate_design_browser
    from .design_fabric import DesignFabricError, operate_design_fabric
    from .design_observer import DesignObserverError, operate_design_observer
    from .design_visual import DesignVisualError, operate_design_visual
    from .simulation import SimulationError, operate_simulation
    from .specialist_pool_extension import build_specialist_pool as _contextual_pool_builder
    from .stepwise_workflow import StepwiseWorkflowError, operate_stepwise_workflow

    # The universal body contains twenty reusable lenses. Allow up to twenty
    # challenge-derived registry specialists so the declared 40-person maximum
    # can actually be reached when enough exact registry matches exist.
    _specialist_pool.MAX_DERIVED_SPECIALISTS = 20

    # Keep challenge-context detection independent of how many specialist
    # profiles the caller chooses to display. Small pools may remain universal,
    # while contextual +1 history still binds to the actual matched domains.
    _specialist_pool.build_specialist_pool = _contextual_pool_builder

    stepwise_operations = {
        "start",
        "start-workflow",
        "checkpoint",
        "prepare-checkpoint",
        "record-analysis",
        "record-checkpoint",
        "execute",
        "execute-step",
        "record-result",
        "result",
        "split",
        "split-step",
        "replan",
        "replan-remaining",
        "instant",
        "run-instant",
        "instant-staged",
        "inspect",
        "summary",
        "prepare-workflow",
        "plan-tournament",
    }
    chameleon_operations = {
        "morph-thoughts",
        "continuous-morph",
        "morph-vector-cells",
        "morph-cells",
        "chameleon-morph",
        "compile-material-graph",
        "compile-material",
        "rich-material",
        "apply-material-graph",
        "apply-material",
        "adapt-environment",
        "sensor-adapt",
        "environment-adapt",
        "compare-reality",
        "reality-feedback",
        "simulation-reality-feedback",
        "recalibrate-simulation",
        "reopen-from-reality",
        "re-simulate-reality-gap",
        "record-calibration",
        "learn-exact-context",
        "inspect-calibrations",
        "calibration-history",
    }
    design_observer_operations = {
        "inspect-observer",
        "record-render-observation",
        "judge-rendered",
        "propose-repair",
    }
    design_browser_operations = {"capture-browser"}
    design_visual_operations = {
        "inspect-visual-observer",
        "observe-screenshot",
        "derive-screenshot-genome",
        "observe-render-screenshot",
    }

    def multi_perspective_orchestration(root, inputs):
        operation = str(inputs.get("operation", "prepare")).strip().casefold()
        is_stepwise = operation in stepwise_operations or (
            operation == "prepare" and ("goal" in inputs or "request" in inputs)
        )
        try:
            if is_stepwise:
                return operate_stepwise_workflow(root, inputs)
            return _specialist_pool.operate_specialist_tournament(root, inputs)
        except (StepwiseWorkflowError, ValueError, TypeError) as exc:
            details = getattr(exc, "details", {})
            raise _capabilities.CapabilityError(str(exc), details) from exc

    def adaptive_simulation_surface(root, inputs):
        operation = str(inputs.get("operation", "simulate-creation")).strip().casefold()
        try:
            if operation in chameleon_operations:
                return operate_chameleon(root, inputs)
            return operate_simulation(root, inputs)
        except (ChameleonError, SimulationError, ValueError, TypeError) as exc:
            details = getattr(exc, "details", {})
            raise _capabilities.CapabilityError(str(exc), details) from exc

    def design_fabric_surface(root, inputs):
        operation = str(inputs.get("operation", "")).strip().casefold()
        try:
            if operation in design_browser_operations:
                return operate_design_browser(root, inputs)
            if operation in design_observer_operations:
                return operate_design_observer(inputs)
            if operation in design_visual_operations:
                return operate_design_visual(root, inputs)
            return operate_design_fabric(root, inputs)
        except (DesignBrowserError, DesignFabricError, DesignObserverError, DesignVisualError, ValueError, TypeError) as exc:
            details = getattr(exc, "details", {})
            raise _capabilities.CapabilityError(str(exc), details) from exc

    _capabilities.BUILTINS["builtin:specialist_tournament"] = multi_perspective_orchestration
    _capabilities.BUILTINS["builtin:simulate_creation"] = adaptive_simulation_surface
    _capabilities.BUILTINS["builtin:design_fabric"] = design_fabric_surface


_register_extension_builtins()
