from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
from typing import Any

from .procedural_3d import GLB_MAGIC, GLB_VERSION, JSON_CHUNK, BIN_CHUNK, verify_glb


SCHEMA = "axm.rigid-scene-graph/v0.1"
_ID_LIMIT = 120


class RigidSceneGraphError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RigidSceneGraphError("scene-graph data must be finite JSON") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _split_glb(body: bytes) -> tuple[dict[str, Any], bytes]:
    if not isinstance(body, (bytes, bytearray)) or len(body) < 28:
        raise RigidSceneGraphError("input GLB is truncated")
    body = bytes(body)
    magic, version, declared = struct.unpack_from("<4sII", body, 0)
    if magic != GLB_MAGIC or version != GLB_VERSION or declared != len(body):
        raise RigidSceneGraphError("input GLB header is invalid")
    json_length, json_type = struct.unpack_from("<II", body, 12)
    if json_type != JSON_CHUNK or json_length <= 0 or json_length % 4:
        raise RigidSceneGraphError("input GLB JSON chunk is invalid")
    json_start, json_end = 20, 20 + json_length
    if json_end + 8 > len(body):
        raise RigidSceneGraphError("input GLB JSON chunk exceeds container")
    bin_length, bin_type = struct.unpack_from("<II", body, json_end)
    bin_start, bin_end = json_end + 8, json_end + 8 + bin_length
    if bin_type != BIN_CHUNK or bin_length < 0 or bin_length % 4 or bin_end != len(body):
        raise RigidSceneGraphError("input GLB BIN chunk is invalid")
    try:
        document = json.loads(body[json_start:json_end].rstrip(b" \x00").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RigidSceneGraphError("input GLB JSON cannot be decoded") from exc
    if not isinstance(document, dict):
        raise RigidSceneGraphError("input GLB JSON root must be an object")
    return document, body[bin_start:bin_end]


def _encode_glb(document: dict[str, Any], bin_chunk: bytes) -> bytes:
    json_bytes = _canonical(document)
    json_padded = json_bytes + b" " * ((-len(json_bytes)) % 4)
    bin_padded = bytes(bin_chunk) + b"\x00" * ((-len(bin_chunk)) % 4)
    total = 12 + 8 + len(json_padded) + 8 + len(bin_padded)
    return (
        struct.pack("<4sII", GLB_MAGIC, GLB_VERSION, total)
        + struct.pack("<II", len(json_padded), JSON_CHUNK)
        + json_padded
        + struct.pack("<II", len(bin_padded), BIN_CHUNK)
        + bin_padded
    )


def _vec(value: Any, label: str, width: int) -> list[float]:
    if not isinstance(value, list) or len(value) != width:
        raise RigidSceneGraphError(f"{label} must contain exactly {width} numbers")
    result: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise RigidSceneGraphError(f"{label}[{index}] must be a finite number")
        item = float(item)
        if not math.isfinite(item) or abs(item) > 1_000_000:
            raise RigidSceneGraphError(f"{label}[{index}] is outside the bounded finite range")
        result.append(item)
    return result


def _normalize_manifest(raw: Any, available_names: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schema", "nodes"}:
        raise RigidSceneGraphError("manifest fields must be exactly schema and nodes")
    if raw.get("schema") != SCHEMA:
        raise RigidSceneGraphError("unsupported rigid scene-graph schema", {"expected": SCHEMA})
    rows = raw.get("nodes")
    if not isinstance(rows, list) or not rows:
        raise RigidSceneGraphError("manifest.nodes must contain at least one node binding")
    if len(rows) > 128:
        raise RigidSceneGraphError("manifest.nodes exceeds the bounded 128-node limit")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RigidSceneGraphError(f"manifest.nodes[{index}] must be an object")
        if not {"name", "parent"} <= set(row) or set(row) - {"name", "parent", "translation", "rotation"}:
            raise RigidSceneGraphError(
                f"manifest.nodes[{index}] fields must be name, parent, optional translation and optional rotation"
            )
        name = row.get("name")
        parent = row.get("parent")
        if not isinstance(name, str) or not name or len(name) > _ID_LIMIT:
            raise RigidSceneGraphError(f"manifest.nodes[{index}].name is invalid")
        if name in seen:
            raise RigidSceneGraphError("manifest node names must be unique", {"duplicate": name})
        if name not in available_names:
            raise RigidSceneGraphError("manifest references a node absent from the input GLB", {"name": name})
        if parent is not None and (not isinstance(parent, str) or parent not in available_names or parent == name):
            raise RigidSceneGraphError("manifest parent must be null or a different existing node", {"name": name, "parent": parent})
        seen.add(name)
        item: dict[str, Any] = {"name": name, "parent": parent}
        if "translation" in row:
            item["translation"] = _vec(row["translation"], f"manifest.nodes[{index}].translation", 3)
        if "rotation" in row:
            rotation = _vec(row["rotation"], f"manifest.nodes[{index}].rotation", 4)
            norm = math.sqrt(sum(value * value for value in rotation))
            if abs(norm - 1.0) > 1e-6:
                raise RigidSceneGraphError("rotation quaternion must be unit length", {"name": name, "norm": norm})
            item["rotation"] = rotation
        normalized.append(item)

    parent_by_name = {row["name"]: row["parent"] for row in normalized}
    for start in parent_by_name:
        trail: set[str] = set()
        cursor: str | None = start
        while cursor in parent_by_name:
            if cursor in trail:
                raise RigidSceneGraphError("manifest parent graph contains a cycle", {"start": start})
            trail.add(cursor)
            cursor = parent_by_name[cursor]
    normalized.sort(key=lambda row: row["name"])
    return {"schema": SCHEMA, "nodes": normalized}


def _graph_snapshot(document: dict[str, Any]) -> dict[str, Any]:
    nodes = document.get("nodes")
    scenes = document.get("scenes")
    scene_index = document.get("scene")
    if not isinstance(nodes, list) or not nodes:
        raise RigidSceneGraphError("input GLB must contain nodes")
    if not isinstance(scenes, list) or type(scene_index) is not int or not 0 <= scene_index < len(scenes):
        raise RigidSceneGraphError("input GLB must contain one selected scene")
    selected = scenes[scene_index]
    if not isinstance(selected, dict) or not isinstance(selected.get("nodes"), list):
        raise RigidSceneGraphError("selected input GLB scene is invalid")
    names: list[str] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise RigidSceneGraphError("input GLB node is invalid", {"index": index})
        name = node.get("name")
        if not isinstance(name, str) or not name:
            raise RigidSceneGraphError("input GLB nodes require stable names", {"index": index})
        if name in names:
            raise RigidSceneGraphError("input GLB node names must be unique", {"name": name})
        if "children" in node or "matrix" in node or "rotation" in node:
            raise RigidSceneGraphError(
                "input GLB is not the bounded flat UC scene expected by this rebind tool",
                {"node": name},
            )
        names.append(name)
    roots = selected["nodes"]
    if sorted(roots) != list(range(len(nodes))) or any(type(index) is not int for index in roots):
        raise RigidSceneGraphError("input GLB selected scene must expose every node exactly once as a root")
    return {"names": names, "roots": list(roots), "scene_index": scene_index}


def rebind_rigid_scene_graph(
    body: bytes,
    manifest: Any,
    *,
    expected_spec_digest: str | None = None,
) -> dict[str, Any]:
    baseline_verification = verify_glb(bytes(body), expected_spec_digest=expected_spec_digest)
    document, bin_chunk = _split_glb(bytes(body))
    snapshot = _graph_snapshot(document)
    names = snapshot["names"]
    name_to_index = {name: index for index, name in enumerate(names)}
    normalized = _normalize_manifest(manifest, set(names))
    manifest_digest = _sha256(_canonical(normalized))

    rebound = copy.deepcopy(document)
    nodes = rebound["nodes"]
    scene = rebound["scenes"][snapshot["scene_index"]]
    parent_index: dict[int, int] = {}
    for row in normalized["nodes"]:
        index = name_to_index[row["name"]]
        parent = row["parent"]
        if parent is not None:
            parent_index[index] = name_to_index[parent]
        if "translation" in row:
            nodes[index]["translation"] = list(row["translation"])
        if "rotation" in row:
            nodes[index]["rotation"] = list(row["rotation"])

    children_by_parent: dict[int, list[int]] = {}
    for child, parent in parent_index.items():
        children_by_parent.setdefault(parent, []).append(child)
    for parent, children in children_by_parent.items():
        nodes[parent]["children"] = sorted(children)
    scene["nodes"] = [index for index in range(len(nodes)) if index not in parent_index]

    extras = rebound.setdefault("extras", {})
    if not isinstance(extras, dict):
        raise RigidSceneGraphError("input GLB extras must be an object when present")
    extras["axmRigidSceneGraphSchema"] = SCHEMA
    extras["axmRigidSceneGraphSha256"] = manifest_digest

    output = _encode_glb(rebound, bin_chunk)
    output_verification = verify_glb(output, expected_spec_digest=baseline_verification["specification_sha256"])
    verified = verify_rigid_scene_graph(output, expected_manifest_digest=manifest_digest)
    if output_verification["triangles"] != baseline_verification["triangles"]:
        raise RigidSceneGraphError("triangle count changed during scene-graph rebind")
    _document_after, bin_after = _split_glb(output)
    if bin_after != bin_chunk:
        raise RigidSceneGraphError("binary geometry payload changed during scene-graph rebind")

    return {
        "body": output,
        "manifest": normalized,
        "manifest_sha256": manifest_digest,
        "receipt": {
            "schema": "axm.rigid-scene-graph-receipt/v0.1",
            "result": "PASS_RIGID_SCENE_GRAPH_REBIND",
            "input_glb_sha256": _sha256(bytes(body)),
            "output_glb_sha256": _sha256(output),
            "manifest_sha256": manifest_digest,
            "binary_chunk_sha256": _sha256(bin_chunk),
            "binary_geometry_payload_identical": True,
            "triangles_before": baseline_verification["triangles"],
            "triangles_after": output_verification["triangles"],
            "nodes_rebound": len(normalized["nodes"]),
            "parent_edges": len(parent_index),
            "scene_roots_after": [names[index] for index in rebound["scenes"][snapshot["scene_index"]]["nodes"]],
            "verified_graph": verified,
            "truth_boundary": {
                "caller_authored_node_names_parents_and_transforms": True,
                "uc_inferred_domain_ownership": False,
                "mesh_or_material_bytes_reauthored": False,
                "animation_clip_authored": False,
                "runtime_controller_or_gameplay_proven": False,
                "host_import_or_visual_quality_proven": False,
            },
        },
    }


def verify_rigid_scene_graph(body: bytes, *, expected_manifest_digest: str | None = None) -> dict[str, Any]:
    verify_glb(bytes(body))
    document, _bin_chunk = _split_glb(bytes(body))
    nodes = document.get("nodes")
    scenes = document.get("scenes")
    scene_index = document.get("scene")
    if not isinstance(nodes, list) or not isinstance(scenes, list) or type(scene_index) is not int or not 0 <= scene_index < len(scenes):
        raise RigidSceneGraphError("rebound GLB scene structure is invalid")
    names = [node.get("name") if isinstance(node, dict) else None for node in nodes]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise RigidSceneGraphError("rebound GLB node names are invalid or duplicate")
    parent_of: dict[int, int] = {}
    for parent, node in enumerate(nodes):
        children = node.get("children", [])
        if not isinstance(children, list) or any(type(child) is not int or not 0 <= child < len(nodes) for child in children):
            raise RigidSceneGraphError("rebound GLB child references are invalid", {"parent": names[parent]})
        if len(set(children)) != len(children):
            raise RigidSceneGraphError("rebound GLB repeats a child reference", {"parent": names[parent]})
        for child in children:
            if child in parent_of:
                raise RigidSceneGraphError("rebound GLB node has multiple parents", {"child": names[child]})
            parent_of[child] = parent
    for start in range(len(nodes)):
        trail: set[int] = set()
        cursor = start
        while cursor in parent_of:
            if cursor in trail:
                raise RigidSceneGraphError("rebound GLB scene graph contains a cycle", {"node": names[start]})
            trail.add(cursor)
            cursor = parent_of[cursor]
    roots = scenes[scene_index].get("nodes") if isinstance(scenes[scene_index], dict) else None
    expected_roots = [index for index in range(len(nodes)) if index not in parent_of]
    if not isinstance(roots, list) or sorted(roots) != expected_roots:
        raise RigidSceneGraphError("rebound GLB scene roots do not match parent relationships")
    extras = document.get("extras")
    if not isinstance(extras, dict) or extras.get("axmRigidSceneGraphSchema") != SCHEMA:
        raise RigidSceneGraphError("rebound GLB lacks the rigid scene-graph provenance marker")
    digest = extras.get("axmRigidSceneGraphSha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise RigidSceneGraphError("rebound GLB lacks a valid rigid scene-graph digest")
    if expected_manifest_digest is not None and digest != expected_manifest_digest:
        raise RigidSceneGraphError("rigid scene-graph digest does not match expected manifest")
    return {
        "result": "PASS_RIGID_SCENE_GRAPH_STRUCTURE",
        "schema": SCHEMA,
        "manifest_sha256": digest,
        "nodes": len(nodes),
        "parent_edges": len(parent_of),
        "roots": [names[index] for index in roots],
        "parent_by_child": {names[child]: names[parent] for child, parent in sorted(parent_of.items())},
        "scope": "named rigid node hierarchy and transforms only; no animation, physics, host import, gameplay or visual-quality claim",
    }
