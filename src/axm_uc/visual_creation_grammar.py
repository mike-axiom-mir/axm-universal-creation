from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

VISUAL_GRAMMAR_SCHEMA = "axm.visual-creation-grammar/v0.2"
VISUAL_RECIPE_SCHEMA = "axm.visual-creation-recipe/v0.2"
VISUAL_QUALITY_LOOP_SCHEMA = "axm.visual-quality-loop/v0.2"

DECOMPOSITION_MODES = (
    "assembled",
    "exploded",
    "cutaway",
    "cross-section",
    "xray",
    "anatomy",
    "ingredient-breakdown",
    "layer-breakdown",
    "deconstructed",
)

CAMERA_MODES = (
    "hero",
    "isometric",
    "top-down",
    "macro",
    "studio",
    "cinematic",
    "close-up",
    "motion-freeze",
)

INFORMATION_MODES = (
    "none",
    "infographic",
    "labeled-diagram",
    "comparison",
    "before-after",
    "feature-callouts",
)

COMMERCIAL_MODES = (
    "none",
    "product-showcase",
    "product-lineup",
    "menu",
    "price-card",
    "product-poster",
    "promo-poster",
    "billboard",
    "magazine-ad",
    "packaging",
)

STYLE_MODES = (
    "neutral",
    "concept-art",
    "blueprint",
    "minimalist",
    "editorial",
    "moody",
    "vibrant",
    "monochrome",
    "retrofuturistic",
    "texture-focus",
    "brand-led",
    "typography-led",
    "abstract",
    "food",
)

ENVIRONMENT_MODES = (
    "neutral",
    "studio",
    "lifestyle",
    "custom-scene",
    "floating",
    "levitating",
    "splash",
)

DEFAULT_TEMPORAL_BEATS = (
    "opener",
    "setup",
    "first-action",
    "turning-point",
    "progress",
    "unique-angle",
    "final-action",
    "reveal",
)

QUALITY_STAGES = (
    "REFERENCE",
    "GRAMMAR",
    "BUILD",
    "RENDER",
    "INSPECT",
    "GAP",
    "GENERALIZE",
    "REPLAY",
)

VISUAL_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "explodedview": {"decomposition": ("exploded",), "camera": ("isometric",)},
    "productshowcase": {"commercial": ("product-showcase",), "camera": ("hero",)},
    "heroshot": {"camera": ("hero",)},
    "cutawayview": {"decomposition": ("cutaway",)},
    "crosssection": {"decomposition": ("cross-section",)},
    "ingredientbreakdown": {"decomposition": ("ingredient-breakdown",), "information": ("labeled-diagram",)},
    "layerbreakdown": {"decomposition": ("layer-breakdown",), "information": ("labeled-diagram",)},
    "floatingcomposition": {"environment": ("floating",)},
    "deconstructed": {"decomposition": ("deconstructed",)},
    "assemblyview": {"decomposition": ("assembled",), "camera": ("isometric",)},
    "infographic": {"information": ("infographic",)},
    "productdiagram": {"information": ("labeled-diagram",)},
    "anatomyof": {"decomposition": ("anatomy",), "information": ("labeled-diagram",)},
    "comparisongraphic": {"information": ("comparison",)},
    "beforeandafter": {"information": ("before-after",)},
    "productposter": {"commercial": ("product-poster",)},
    "promoposter": {"commercial": ("promo-poster",)},
    "billboardad": {"commercial": ("billboard",)},
    "magazinead": {"commercial": ("magazine-ad",)},
    "packagingdesign": {"commercial": ("packaging",)},
    "menudesign": {"commercial": ("menu",)},
    "pricecard": {"commercial": ("price-card",)},
    "featurecallouts": {"information": ("feature-callouts",)},
    "isometricview": {"camera": ("isometric",)},
    "topdownflatlay": {"camera": ("top-down",)},
    "macroshot": {"camera": ("macro",)},
    "studioshot": {"camera": ("studio",), "environment": ("studio",)},
    "cinematicshot": {"camera": ("cinematic",)},
    "minimalistposter": {"style": ("minimalist",)},
    "editoriallayout": {"style": ("editorial",)},
    "3drender": {"camera": ("hero",), "environment": ("studio",)},
    "conceptart": {"style": ("concept-art",)},
    "blueprintstyle": {"style": ("blueprint",), "information": ("labeled-diagram",)},
    "xrayview": {"decomposition": ("xray",)},
    "productlineup": {"commercial": ("product-lineup",)},
    "splashshot": {"environment": ("splash",), "camera": ("motion-freeze",)},
    "levitationshot": {"environment": ("levitating",), "camera": ("hero",)},
    "motionfreeze": {"camera": ("motion-freeze",)},
    "closeupshot": {"camera": ("close-up",)},
    "lifestylephoto": {"environment": ("lifestyle",)},
    "moodyshot": {"style": ("moody",)},
    "vibrantcolors": {"style": ("vibrant",)},
    "blackandwhite": {"style": ("monochrome",)},
    "retrofuturistic": {"style": ("retrofuturistic",)},
    "foodphotography": {"style": ("food",)},
    "texturefocus": {"style": ("texture-focus",), "camera": ("macro",)},
    "brandidentity": {"style": ("brand-led",)},
    "typographyposter": {"style": ("typography-led",)},
    "abstractart": {"style": ("abstract",)},
    "customscene": {"environment": ("custom-scene",)},
}


def _hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stable_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _tokens(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise TypeError("visual grammar axis must be a string or list of strings")
    return [str(item).strip().casefold() for item in value if str(item).strip()]


def _validated_axis(value: Any, allowed: tuple[str, ...], field: str) -> list[str]:
    tokens = _tokens(value)
    unknown = [item for item in tokens if item not in allowed]
    if unknown:
        raise ValueError(f"unknown {field}: {', '.join(unknown)}")
    return _stable_unique(tokens)


def _aliases(value: Any) -> list[str]:
    aliases = _tokens(value)
    unknown = [item for item in aliases if item not in VISUAL_ALIASES]
    if unknown:
        raise ValueError(f"unknown visual alias: {', '.join(unknown)}")
    return _stable_unique(aliases)


def _duration_plan(beats: list[str], seconds: float) -> list[dict[str, Any]]:
    if not beats:
        return []
    if seconds <= 0:
        raise ValueError("temporal duration_seconds must be greater than zero")
    total_ms = int(round(seconds * 1000))
    base = total_ms // len(beats)
    remainder = total_ms % len(beats)
    cursor = 0
    rows = []
    for index, beat in enumerate(beats):
        duration_ms = base + (1 if index < remainder else 0)
        rows.append({
            "index": index,
            "beat": beat,
            "start_ms": cursor,
            "duration_ms": duration_ms,
            "end_ms": cursor + duration_ms,
        })
        cursor += duration_ms
    return rows


def grammar_catalog() -> dict[str, Any]:
    core = {
        "schema": VISUAL_GRAMMAR_SCHEMA,
        "truth_status": "EXECUTABLE_COMPOSITION_GRAMMAR",
        "axes": {
            "decomposition": list(DECOMPOSITION_MODES),
            "camera": list(CAMERA_MODES),
            "information": list(INFORMATION_MODES),
            "commercial": list(COMMERCIAL_MODES),
            "style": list(STYLE_MODES),
            "environment": list(ENVIRONMENT_MODES),
            "temporal_beats": list(DEFAULT_TEMPORAL_BEATS),
        },
        "aliases": {key: {axis: list(values) for axis, values in value.items()} for key, value in VISUAL_ALIASES.items()},
        "quality_loop": list(QUALITY_STAGES),
        "truth": {
            "aliasesAreGrammarCompositionsNotSeparateOrgans": True,
            "naturalLanguageSemanticParsingImplemented": False,
            "renderingImplementedByThisModule": False,
            "visualQualityJudgementImplementedByThisModule": False,
            "automaticPromotion": False,
        },
    }
    return {**core, "catalog_sha256": _hash(core)}


def _merge_alias_axes(aliases: list[str]) -> dict[str, list[str]]:
    merged = {axis: [] for axis in ("decomposition", "camera", "information", "commercial", "style", "environment")}
    for alias in aliases:
        for axis, values in VISUAL_ALIASES[alias].items():
            merged[axis].extend(values)
    return {axis: _stable_unique(values) for axis, values in merged.items()}


def _generator_hints(axes: dict[str, list[str]], temporal_enabled: bool) -> list[str]:
    hints = ["mesh", "vector-part"]
    if axes["style"] or axes["environment"]:
        hints.extend(["surface", "pigment", "material", "palette", "gradient"])
    if axes["information"] != ["none"] or axes["commercial"] != ["none"]:
        hints.extend(["vector-part", "palette", "gradient"])
    if "texture-focus" in axes["style"] or "macro" in axes["camera"] or "close-up" in axes["camera"]:
        hints.extend(["surface", "pigment", "material"])
    if temporal_enabled:
        hints.append("sprite")
    return _stable_unique(hints)


def compile_visual_recipe(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise TypeError("visual recipe request must be an object")
    subject = str(request.get("subject", "")).strip()
    if not subject:
        raise ValueError("visual recipe requires a non-empty subject")

    aliases = _aliases(request.get("aliases"))
    alias_axes = _merge_alias_axes(aliases)
    explicit = {
        "decomposition": _validated_axis(request.get("decomposition"), DECOMPOSITION_MODES, "decomposition mode"),
        "camera": _validated_axis(request.get("camera"), CAMERA_MODES, "camera mode"),
        "information": _validated_axis(request.get("information"), INFORMATION_MODES, "information mode"),
        "commercial": _validated_axis(request.get("commercial"), COMMERCIAL_MODES, "commercial mode"),
        "style": _validated_axis(request.get("style"), STYLE_MODES, "style mode"),
        "environment": _validated_axis(request.get("environment"), ENVIRONMENT_MODES, "environment mode"),
    }
    axes = {axis: _stable_unique(alias_axes[axis] + explicit[axis]) for axis in explicit}
    if not axes["decomposition"]:
        axes["decomposition"] = ["assembled"]
    if not axes["camera"]:
        axes["camera"] = ["hero"]
    if not axes["information"]:
        axes["information"] = ["none"]
    if not axes["commercial"]:
        axes["commercial"] = ["none"]
    if not axes["style"]:
        axes["style"] = ["neutral"]
    if not axes["environment"]:
        axes["environment"] = ["neutral"]

    temporal = request.get("temporal")
    if temporal is None:
        temporal = {}
    if not isinstance(temporal, dict):
        raise TypeError("temporal must be an object")
    temporal_enabled = bool(temporal.get("enabled", False))
    beats = _tokens(temporal.get("beats")) if temporal_enabled else []
    if temporal_enabled and not beats:
        beats = list(DEFAULT_TEMPORAL_BEATS)
    if temporal_enabled:
        unknown_beats = [beat for beat in beats if beat not in DEFAULT_TEMPORAL_BEATS]
        if unknown_beats:
            raise ValueError(f"unknown temporal beat: {', '.join(unknown_beats)}")
        beats = _stable_unique(beats)
        duration_seconds = float(temporal.get("duration_seconds", 10.0))
        timeline = _duration_plan(beats, duration_seconds)
    else:
        duration_seconds = 0.0
        timeline = []

    references = _stable_unique(_tokens(request.get("references")))
    criteria = _stable_unique(_tokens(request.get("criteria")))
    constraints = _stable_unique(_tokens(request.get("constraints")))
    avoid = _stable_unique(_tokens(request.get("avoid")))
    technical_requirements = request.get("technical_requirements") or {}
    if not isinstance(technical_requirements, dict):
        raise TypeError("technical_requirements must be an object")
    scene = request.get("scene") or {}
    if not isinstance(scene, dict):
        raise TypeError("scene must be an object")
    scene_director = {
        "focus": str(scene.get("focus", subject)).strip() or subject,
        "lighting": str(scene.get("lighting", "AUTO_FROM_STYLE")).strip(),
        "atmosphere": str(scene.get("atmosphere", "AUTO_FROM_STYLE")).strip(),
        "environment_notes": str(scene.get("environment_notes", "")).strip(),
        "camera_sequence": list(axes["camera"]),
        "layer_order": [
            "environment",
            "subject-geometry",
            "surface-material",
            "lighting-atmosphere",
            "camera",
            "information-overlay",
            "brand-overlay",
            "temporal-motion",
        ],
    }

    quality_loop = {
        "schema": VISUAL_QUALITY_LOOP_SCHEMA,
        "stages": [
            {"stage": "REFERENCE", "status": "DEFINED" if references else "OPTIONAL_NOT_SUPPLIED", "evidence": references},
            {"stage": "GRAMMAR", "status": "COMPILED"},
            {"stage": "BUILD", "status": "PENDING_EXECUTOR"},
            {"stage": "RENDER", "status": "PENDING_RENDER_HOST"},
            {"stage": "INSPECT", "status": "PENDING_VISUAL_OR_INTERACTION_EVIDENCE", "criteria": criteria},
            {"stage": "GAP", "status": "PENDING_OBSERVATION"},
            {"stage": "GENERALIZE", "status": "PENDING_EXPLICIT_GAP"},
            {"stage": "REPLAY", "status": "PENDING_EXPLICIT_ADOPTION"},
        ],
        "truth": {
            "referencePresenceIsNotQualityProof": True,
            "renderReceiptIsNotVisualQualityProof": True,
            "gapMustComeFromObservedEvidence": True,
            "gameSpecificFixShouldPreferGeneralCapabilityWhenSupported": True,
            "automaticPromotion": False,
        },
    }

    core = {
        "schema": VISUAL_RECIPE_SCHEMA,
        "subject": subject,
        "seed": int(request.get("seed", 0)),
        "aliases": aliases,
        "axes": axes,
        "scene_director": scene_director,
        "temporal": {
            "enabled": temporal_enabled,
            "duration_seconds": duration_seconds,
            "timeline": timeline,
        },
        "generator_hints": _generator_hints(axes, temporal_enabled),
        "constraints": constraints,
        "avoid": avoid,
        "technical_requirements": technical_requirements,
        "quality_loop": quality_loop,
        "truth": {
            "structuredRequestRequired": True,
            "naturalLanguageSemanticParsingImplemented": False,
            "recipeIsNotRenderedArtifact": True,
            "sceneDirectorIsPlanNotCameraExecution": True,
            "generatorHintsAreNotExecution": True,
            "visualQualityJudged": False,
            "automaticExecution": False,
            "automaticPromotion": False,
        },
    }
    return {**core, "recipe_sha256": _hash(core)}
