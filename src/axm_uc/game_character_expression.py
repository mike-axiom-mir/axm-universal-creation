"""Deterministic facial expression and storytelling stance composition.

The capability operates on explicit component semantics and pivots.  It never
infers a face or skeleton from geometry.  Protected identity components receive
only their parent's rigid stance transform; expression scaling and local stance
rules cannot rewrite them.  Canonical source and authored controls remain
embedded beside the derived static pose.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import tempfile

from .atomic import atomic_write_bytes, atomic_write_json
from .procedural_3d import build_glb


CHARACTER_EXPRESSION_SCHEMA = "axm.game-character-expression/v0.1"
ROLES = ("body", "head", "arm", "leg", "prop", "face-shell", "eye", "brow", "mouth", "identity", "detail")
SIDES = ("left", "center", "right")


@dataclass(frozen=True)
class ExpressionProfile:
    name: str
    eye_scale_x: float
    left_eye_scale_y: float
    right_eye_scale_y: float
    left_brow_degrees: float
    right_brow_degrees: float
    brow_lift: float
    mouth_scale_x: float
    mouth_scale_y: float
    mouth_degrees: float
    mouth_lift: float


@dataclass(frozen=True)
class StanceProfile:
    name: str
    body_translation: tuple[float, float, float]
    body_degrees: tuple[float, float, float]
    head_degrees: tuple[float, float, float]
    left_arm_degrees: tuple[float, float, float]
    right_arm_degrees: tuple[float, float, float]
    left_leg_degrees: tuple[float, float, float]
    right_leg_degrees: tuple[float, float, float]
    prop_degrees: tuple[float, float, float]


EXPRESSIONS = (
    ExpressionProfile("neutral", 1, 1, 1, 0, 0, 0, 1, 1, 0, 0),
    ExpressionProfile("curious", 1.08, 1.32, .78, -9, 13, .045, .76, .82, 7, -.015),
    ExpressionProfile("mischief", 1.10, 1.02, .24, 12, -19, .015, 1.30, .62, -9, .018),
    ExpressionProfile("alarmed", 1.24, 1.28, 1.28, -5, 5, .105, .68, 1.58, 0, -.035),
    ExpressionProfile("determined", 1.02, .68, .68, -17, 17, -.025, .94, .44, 0, -.015),
)

STANCES = (
    StanceProfile("neutral", (0, 0, 0), (0, 0, 0), (0, 0, 0),
                  (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)),
    StanceProfile("mechanic-ready", (0, -.06, .08), (8, 0, 0), (-5, 0, 0),
                  (0, 0, -28), (0, 0, 18), (0, 0, -5), (0, 0, 5), (0, 0, -12)),
    StanceProfile("comic-sneak", (0, -.24, .16), (14, 0, -3), (-11, 0, 7),
                  (0, 0, 24), (0, 0, -34), (0, 0, 13), (0, 0, -10), (0, 0, 18)),
    StanceProfile("victory", (0, .09, 0), (-4, 0, 0), (0, 0, 7),
                  (0, 0, -104), (0, 0, 104), (0, 0, -6), (0, 0, 6), (0, 0, 16)),
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _number(value, label, low=-100000.0, high=100000.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _vec3(value, label, low=-100000.0, high=100000.0):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must have three coordinates")
    return tuple(_number(item, f"{label}[{index}]", low, high) for index, item in enumerate(value))


def _component(primitive):
    identifier = primitive.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("every primitive needs a non-empty id")
    return identifier.split("__", 1)[0]


def _profile(items, name, label):
    for item in items:
        if item.name == name:
            return item
    raise ValueError(f"unknown {label}: {name}")


def game_character_expression_catalog():
    return {
        "schema": "axm.game-character-expression-catalog/v0.1",
        "expressions": [asdict(item) for item in EXPRESSIONS],
        "stances": [asdict(item) for item in STANCES],
        "roles": list(ROLES),
        "sides": list(SIDES),
        "canonical_source_preserved": True,
        "identity_contract": (
            "Caller-declared protected components keep rigid shape and pairwise pivot relationships; "
            "authored eye pivots preserve spacing through expressions."
        ),
        "truth": (
            "Produces deterministic static geometry poses from explicit semantics. It does not infer a rig, "
            "prove animation deformation, contacts, collision, gameplay readability or artistic quality."
        ),
    }


def _mesh_components(mesh):
    if not isinstance(mesh, dict) or mesh.get("schema") != "axm.surface-3d/v0.1":
        raise ValueError("mesh must use axm.surface-3d/v0.1")
    primitives = mesh.get("primitives")
    if not isinstance(primitives, list) or not 1 <= len(primitives) <= 512:
        raise ValueError("mesh needs 1..512 primitives")
    components = {}
    for primitive in primitives:
        if not isinstance(primitive, dict):
            raise ValueError("primitive must be an object")
        component = _component(primitive)
        positions, normals = primitive.get("positions"), primitive.get("normals")
        indices, colors, material = primitive.get("indices"), primitive.get("colors"), primitive.get("material")
        if not isinstance(positions, list) or not positions or len(positions) > 1_000_000:
            raise ValueError(f"{component} positions are missing or over limit")
        checked = [_vec3(point, f"{component}.position") for point in positions]
        if not isinstance(normals, list) or len(normals) != len(positions):
            raise ValueError(f"{component} needs one normal per position")
        for normal in normals:
            _vec3(normal, f"{component}.normal", -1, 1)
        if not isinstance(colors, list) or len(colors) != len(positions) or not isinstance(material, dict):
            raise ValueError(f"{component} colors or material are missing")
        if (not isinstance(indices, list) or not indices or len(indices) % 3 or
                any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(positions) for i in indices)):
            raise ValueError(f"{component} indices must be bounded triangles")
        components.setdefault(component, []).extend(checked)
    build_glb(mesh)
    return components


def _part_specs(raw, components):
    if not isinstance(raw, dict) or set(raw) != set(components):
        missing, extra = sorted(set(components) - set(raw)), sorted(set(raw) - set(components))
        raise ValueError(f"part specs must exactly cover components; missing={missing}, unexpected={extra}")
    specs = {}
    for name, value in raw.items():
        if not isinstance(value, dict):
            raise ValueError(f"part {name} must be an object")
        extra = set(value) - {"role", "side", "parent", "pivot", "strength", "identity_protected"}
        if extra:
            raise ValueError(f"part {name} has unsupported fields: {sorted(extra)}")
        role, side, parent = value.get("role"), value.get("side", "center"), value.get("parent")
        if role not in ROLES or side not in SIDES:
            raise ValueError(f"part {name} has unknown role or side")
        if parent is not None and (not isinstance(parent, str) or parent not in components or parent == name):
            raise ValueError(f"part {name} has invalid parent")
        if role in ("eye", "brow") and side not in SIDES:
            raise ValueError(f"part {name} needs a face side")
        if role == "mouth" and side != "center":
            raise ValueError(f"part {name} mouth must be center sided")
        protected = value.get("identity_protected", False)
        if type(protected) is not bool:
            raise ValueError(f"part {name}.identity_protected must be boolean")
        specs[name] = {
            "role": role, "side": side, "parent": parent,
            "pivot": _vec3(value.get("pivot"), f"part {name}.pivot"),
            "strength": _number(value.get("strength", 1), f"part {name}.strength", 0, 1),
            "identity_protected": protected,
        }
    if not any(spec["role"] == "body" for spec in specs.values()):
        raise ValueError("character needs a body component")
    if not any(spec["role"] == "eye" for spec in specs.values()) or not any(spec["role"] == "mouth" for spec in specs.values()):
        raise ValueError("character needs explicit eye and mouth components")
    protected = [spec for spec in specs.values() if spec["identity_protected"]]
    if not protected:
        raise ValueError("character needs at least one protected identity component")
    if len({spec["parent"] for spec in protected}) != 1:
        raise ValueError("protected identity components must share one parent transform")
    visiting, visited = set(), set()
    def visit(name):
        if name in visiting:
            raise ValueError("part parent graph contains a cycle")
        if name in visited:
            return
        visiting.add(name)
        parent = specs[name]["parent"]
        if parent is not None:
            visit(parent)
        visiting.remove(name)
        visited.add(name)
    for name in specs:
        visit(name)
    return specs


def _identity_matrix():
    return ((1., 0., 0., 0.), (0., 1., 0., 0.), (0., 0., 1., 0.), (0., 0., 0., 1.))


def _multiply(a, b):
    return tuple(tuple(sum(a[row][k] * b[k][column] for k in range(4)) for column in range(4)) for row in range(4))


def _translation(value):
    x, y, z = value
    return ((1., 0., 0., x), (0., 1., 0., y), (0., 0., 1., z), (0., 0., 0., 1.))


def _scale(value):
    x, y, z = value
    return ((x, 0., 0., 0.), (0., y, 0., 0.), (0., 0., z, 0.), (0., 0., 0., 1.))


def _rotation(degrees):
    x, y, z = (math.radians(value) for value in degrees)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = ((1, 0, 0, 0), (0, cx, -sx, 0), (0, sx, cx, 0), (0, 0, 0, 1))
    ry = ((cy, 0, sy, 0), (0, 1, 0, 0), (-sy, 0, cy, 0), (0, 0, 0, 1))
    rz = ((cz, -sz, 0, 0), (sz, cz, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
    return _multiply(rz, _multiply(ry, rx))


def _about(pivot, scale=(1, 1, 1), degrees=(0, 0, 0), translation=(0, 0, 0)):
    return _multiply(_translation(translation), _multiply(_translation(pivot),
        _multiply(_rotation(degrees), _multiply(_scale(scale), _translation(tuple(-v for v in pivot))))))


def _point(matrix, point):
    out = tuple(sum(matrix[row][axis] * point[axis] for axis in range(3)) + matrix[row][3] for row in range(3))
    return tuple(round(value, 9) for value in out)


def _normal(matrix, normal):
    """Transform an authored normal with the inverse transpose of affine 3x3."""
    a, b, c = matrix[0][:3]
    d, e, f = matrix[1][:3]
    g, h, i = matrix[2][:3]
    cofactors = (
        (e * i - f * h, f * g - d * i, d * h - e * g),
        (c * h - b * i, a * i - c * g, b * g - a * h),
        (b * f - c * e, c * d - a * f, a * e - b * d),
    )
    det = a * cofactors[0][0] + b * cofactors[0][1] + c * cofactors[0][2]
    if abs(det) <= 1e-12:
        raise ValueError("character expression produced a singular normal transform")
    transformed = tuple(sum(cofactors[row][axis] * normal[axis] for axis in range(3)) / det
                        for row in range(3))
    length = math.sqrt(sum(value * value for value in transformed))
    if length <= 1e-12:
        raise ValueError("character expression produced a zero normal")
    return tuple(round(value / length, 9) for value in transformed)


def _stance_local(spec, profile):
    if spec["identity_protected"]:
        return _identity_matrix()
    role, side, strength = spec["role"], spec["side"], spec["strength"]
    degrees, translation = (0, 0, 0), (0, 0, 0)
    if role == "body":
        degrees, translation = profile.body_degrees, profile.body_translation
    elif role == "head":
        degrees = profile.head_degrees
    elif role == "arm":
        degrees = profile.left_arm_degrees if side == "left" else profile.right_arm_degrees if side == "right" else (0, 0, 0)
    elif role == "leg":
        degrees = profile.left_leg_degrees if side == "left" else profile.right_leg_degrees if side == "right" else (0, 0, 0)
    elif role == "prop":
        degrees = profile.prop_degrees
    degrees = tuple(value * strength for value in degrees)
    translation = tuple(value * strength for value in translation)
    return _about(spec["pivot"], degrees=degrees, translation=translation)


def _expression_local(spec, profile):
    if spec["identity_protected"]:
        return _identity_matrix()
    role, side, strength = spec["role"], spec["side"], spec["strength"]
    scale, degrees, translation = (1, 1, 1), (0, 0, 0), (0, 0, 0)
    if role == "eye":
        vertical = (profile.left_eye_scale_y if side == "left" else
                    profile.right_eye_scale_y if side == "right" else
                    (profile.left_eye_scale_y + profile.right_eye_scale_y) * .5)
        scale = (1 + (profile.eye_scale_x - 1) * strength, 1 + (vertical - 1) * strength, 1)
    elif role == "brow":
        angle = profile.left_brow_degrees if side == "left" else profile.right_brow_degrees if side == "right" else 0
        degrees = (0, 0, angle * strength)
        translation = (0, profile.brow_lift * strength, 0)
    elif role == "mouth":
        scale = (1 + (profile.mouth_scale_x - 1) * strength, 1 + (profile.mouth_scale_y - 1) * strength, 1)
        degrees = (0, 0, profile.mouth_degrees * strength)
        translation = (0, profile.mouth_lift * strength, 0)
    return _about(spec["pivot"], scale=scale, degrees=degrees, translation=translation)


def _component_matrices(specs, stance):
    result = {}
    def matrix(name):
        if name in result:
            return result[name]
        spec = specs[name]
        parent = _identity_matrix() if spec["parent"] is None else matrix(spec["parent"])
        result[name] = _multiply(parent, _stance_local(spec, stance))
        return result[name]
    for name in specs:
        matrix(name)
    return result


def _radial_signature(points, pivot):
    return sorted(round(math.dist(point, pivot), 8) for point in points)


def apply_character_expression(mesh, part_specs, expression="mischief", stance="mechanic-ready"):
    """Return canonical source plus one checked static expression/stance realization."""
    expression_profile = _profile(EXPRESSIONS, expression, "expression")
    stance_profile = _profile(STANCES, stance, "stance")
    components = _mesh_components(mesh)
    specs = _part_specs(part_specs, components)
    stance_matrices = _component_matrices(specs, stance_profile)
    source = copy.deepcopy(mesh)
    realization = copy.deepcopy(mesh)
    transformed_components = {}
    for primitive in realization["primitives"]:
        name = _component(primitive)
        if expression == "neutral" and stance == "neutral":
            positions = copy.deepcopy(primitive["positions"])
        else:
            expression_matrix = _expression_local(specs[name], expression_profile)
            composite = _multiply(stance_matrices[name], expression_matrix)
            positions = [list(_point(composite, point)) for point in primitive["positions"]]
            primitive["positions"] = positions
            primitive["normals"] = [list(_normal(composite, normal)) for normal in primitive["normals"]]
        transformed_components.setdefault(name, []).extend(tuple(point) for point in positions)
    protected_names = sorted(name for name, spec in specs.items() if spec["identity_protected"])
    radial_errors = []
    for name in protected_names:
        before = _radial_signature(components[name], specs[name]["pivot"])
        after_pivot = _point(stance_matrices[name], specs[name]["pivot"])
        after = _radial_signature(transformed_components[name], after_pivot)
        radial_errors.append(max(abs(a - b) for a, b in zip(before, after)))
    pair_errors = []
    for index, left in enumerate(protected_names):
        for right in protected_names[index + 1:]:
            before = math.dist(specs[left]["pivot"], specs[right]["pivot"])
            after = math.dist(_point(stance_matrices[left], specs[left]["pivot"]),
                              _point(stance_matrices[right], specs[right]["pivot"]))
            pair_errors.append(abs(before - after))
    eye_rows = []
    for name, spec in sorted(specs.items()):
        if spec["role"] == "eye":
            eye_rows.append({"component": name, "side": spec["side"],
                             "before": list(spec["pivot"]),
                             "after": list(_point(stance_matrices[name], spec["pivot"]))})
    eye_spacing_error = 0.0
    for index, left in enumerate(eye_rows):
        for right in eye_rows[index + 1:]:
            before, after = math.dist(left["before"], right["before"]), math.dist(left["after"], right["after"])
            eye_spacing_error = max(eye_spacing_error, abs(before - after))
    max_radial = max(radial_errors, default=0.0)
    max_pair = max(pair_errors, default=0.0)
    identity_pass = max_radial <= 1e-7 and max_pair <= 1e-7 and eye_spacing_error <= 1e-7
    if not identity_pass:
        raise ValueError("derived character failed protected identity invariants")
    built = build_glb(realization)
    return {
        "schema": CHARACTER_EXPRESSION_SCHEMA,
        "expression": asdict(expression_profile),
        "stance": asdict(stance_profile),
        "source_sha256": _digest(source),
        "source": source,
        "realization": realization,
        "parts": copy.deepcopy(part_specs),
        "identity_receipt": {
            "protected_components": protected_names,
            "maximum_protected_radial_signature_error": max_radial,
            "maximum_protected_pairwise_pivot_distance_error": max_pair,
            "maximum_authored_eye_pivot_spacing_error": eye_spacing_error,
            "authored_eye_pivots": eye_rows,
            "passed": identity_pass,
        },
        "gates": {"canonical-source-embedded": source == mesh,
                  "protected-identity-preserved": identity_pass,
                  "static-glb-valid": bool(built["body"])},
        "truth": (
            "A deterministic static geometry pose from caller-authored roles and pivots. Protected rigid identity "
            "and eye-pivot spacing pass; rigging, animation, contacts, collision and target-engine use remain unproven."
        ),
    }


def publish_character_expression(path, mesh, part_specs, expression="mischief", stance="mechanic-ready"):
    """Transactionally publish canonical source, realization, receipt and actual GLB."""
    target = Path(path).resolve()
    if target.exists():
        raise FileExistsError(f"character expression output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    package = apply_character_expression(mesh, part_specs, expression, stance)
    built = build_glb(package["realization"])
    with tempfile.TemporaryDirectory(prefix=".axm-character-expression-", dir=target.parent) as temporary:
        stage = Path(temporary) / "publication"
        stage.mkdir()
        atomic_write_json(stage / "source.json", package["source"])
        atomic_write_json(stage / "realization.json", package["realization"])
        manifest = {key: value for key, value in package.items() if key not in ("source", "realization")}
        manifest["glb_sha256"] = hashlib.sha256(built["body"]).hexdigest()
        manifest["glb_specification_sha256"] = built["specification_sha256"]
        atomic_write_json(stage / "character-expression.json", manifest)
        atomic_write_bytes(stage / "asset.glb", built["body"])
        os.replace(stage, target)
    return {**manifest, "path": str(target), "files": sorted(item.name for item in target.iterdir())}
