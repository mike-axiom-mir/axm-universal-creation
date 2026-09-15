"""Offline evaluation of a bounded GLB transform/skin subset; no renderer needed.

Quaternions are xyzw; published matrices are row-major, multiplying column
vectors. glTF column-major matrices are converted exactly once on intake.
Source GLB bytes and their material/geometry payloads are never rewritten.
"""
from __future__ import annotations

import bisect
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile

from .atomic import atomic_write_json

MAX_BYTES = 64 * 1024 * 1024
MAX_VALUES = 4_000_000
MAX_VERTICES = 250_000
IDENTITY = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]
DEFAULTS = {"translation": [0., 0., 0.], "rotation": [0., 0., 0., 1.], "scale": [1., 1., 1.]}
WIDTHS = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def game_pose_runtime_catalog():
    return {
        "schema": "axm.game-pose-runtime-catalog/v0.1",
        "executes": ["embedded GLB transform intake", "LINEAR and STEP sampling", "quaternion shortest-arc interpolation",
                     "local pose crossfade", "hierarchical world transforms", "socket points", "linear skin positions"],
        "dependencies": [], "source_preserved": True,
        "matrix_convention": "row-major matrices multiplying column vectors; scene-space output",
        "limits": {"glb_bytes": MAX_BYTES, "nodes": 2048, "decoded_scalars": MAX_VALUES,
                   "instantiated_vertices": MAX_VERTICES},
        "truth": "Evaluates authored poses and vertex positions offline. No shading, normals/tangents, morph targets, "
                 "CUBICSPLINE, IK, physics, automatic transition blending or device playback acceptance. "
                 "Root translation remains in the authored pose; do not apply runtime root displacement a second time.",
    }


def _integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in {low}..{high}")
    return value


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e12:
        raise ValueError(f"{label} must be a bounded finite number")
    return float(value)


def _vector(value, width, label):
    if not isinstance(value, (list, tuple)) or len(value) != width:
        raise ValueError(f"{label} requires {width} numbers")
    return [_number(v, label) for v in value]


def _quaternion(value):
    value = _vector(value, 4, "quaternion")
    length = math.sqrt(sum(v * v for v in value))
    if abs(length - 1) > 1e-4:
        raise ValueError("rotation quaternion must be normalized")
    return [v / length for v in value]


def _slerp(a, b, weight):
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0:
        b, dot = [-v for v in b], -dot
    dot = min(1., dot)
    if dot > .9995:
        result = [x + (y - x) * weight for x, y in zip(a, b)]
    else:
        angle = math.acos(dot)
        result = [(x * math.sin((1 - weight) * angle) + y * math.sin(weight * angle)) / math.sin(angle)
                  for x, y in zip(a, b)]
    length = math.sqrt(sum(v * v for v in result))
    return [v / length for v in result]


def _multiply(a, b):
    return [sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4)]


def _transform(matrix, position):
    return [sum(matrix[r * 4 + k] * position[k] for k in range(3)) + matrix[r * 4 + 3] for r in range(3)]


def _trs(local):
    x, y, z, w = local["rotation"]
    sx, sy, sz = local["scale"]
    tx, ty, tz = local["translation"]
    return [(1 - 2 * (y*y + z*z))*sx, 2*(x*y-z*w)*sy, 2*(x*z+y*w)*sz, tx,
            2*(x*y+z*w)*sx, (1-2*(x*x+z*z))*sy, 2*(y*z-x*w)*sz, ty,
            2*(x*z-y*w)*sx, 2*(y*z+x*w)*sy, (1-2*(x*x+y*y))*sz, tz, 0., 0., 0., 1.]


def _matrix(value):
    source = _vector(value, 16, "matrix")
    result = [source[c * 4 + r] for r in range(4) for c in range(4)]
    if result[12:] != [0, 0, 0, 1]:
        raise ValueError("only affine matrices are supported")
    return result


def _array(document, key, maximum):
    value = document.get(key, [])
    if not isinstance(value, list) or len(value) > maximum or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"{key} must be a bounded array of objects")
    return value


def _parse(body):
    if not isinstance(body, bytes) or not 28 <= len(body) <= MAX_BYTES:
        raise ValueError("GLB must be bounded bytes")
    if struct.unpack_from("<4sII", body) != (b"glTF", 2, len(body)):
        raise ValueError("invalid GLB header or declared length")
    chunks, offset = [], 12
    while offset < len(body):
        if offset + 8 > len(body):
            raise ValueError("truncated GLB chunk")
        length, kind = struct.unpack_from("<II", body, offset)
        offset += 8
        if length % 4 or offset + length > len(body):
            raise ValueError("invalid GLB chunk bounds")
        chunks.append((kind, body[offset:offset + length]))
        offset += length
    if len(chunks) != 2 or [c[0] for c in chunks] != [0x4E4F534A, 0x004E4942] or len(chunks[0][1]) > 4 * 1024 * 1024:
        raise ValueError("requires one JSON chunk followed by one embedded BIN chunk")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate GLB JSON key")
            result[key] = value
        return result
    try:
        document = json.loads(chunks[0][1].decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid GLB JSON") from exc
    if (not isinstance(document, dict) or not isinstance(document.get("asset"), dict)
            or document["asset"].get("version") != "2.0" or document["asset"].get("minVersion", "2.0") != "2.0"):
        raise ValueError("requires glTF 2.0")
    required = document.get("extensionsRequired", [])
    if not isinstance(required, list) or any(not isinstance(x, str) or not
            (x.startswith("KHR_materials_") or x == "KHR_texture_transform") for x in required):
        raise ValueError("unsupported required extension; only non-pose material/texture extensions are accepted")
    buffers = _array(document, "buffers", 1)
    if len(buffers) != 1 or "uri" in buffers[0]:
        raise ValueError("external buffers are unsupported")
    length = _integer(buffers[0].get("byteLength"), "buffer.byteLength", 1, len(chunks[1][1]))
    if len(chunks[1][1]) - length > 3:
        raise ValueError("invalid BIN padding")
    return document, chunks[1][1][:length]


class GamePoseAsset:
    """Compile once, sample repeatedly. Internal arrays never alias caller bytes."""

    def __init__(self, body):
        document, binary = _parse(body)
        self.source_sha256 = hashlib.sha256(body).hexdigest()
        views = _array(document, "bufferViews", 16384)
        accessors = _array(document, "accessors", 16384)
        budget, cache = 0, {}

        def accessor(ref, shape, allowed=(5126,)):
            nonlocal budget
            ref = _integer(ref, "accessor index", 0, len(accessors) - 1)
            a = accessors[ref]
            if (a.get("type") != shape or type(a.get("componentType")) is not int
                    or a["componentType"] not in allowed or "sparse" in a or a.get("extensions")):
                raise ValueError("unsupported accessor shape, component or sparse encoding")
            if type(a.get("normalized", False)) is not bool:
                raise ValueError("normalized must be boolean")
            if a.get("normalized", False) and a["componentType"] == 5126:
                raise ValueError("float accessors cannot be normalized")
            if ref in cache:
                return cache[ref]
            count = _integer(a.get("count"), "accessor.count", 1, MAX_VALUES)
            width = WIDTHS[shape]
            budget += count * width
            if budget > MAX_VALUES:
                raise ValueError("decoded scalar budget exceeded")
            view = views[_integer(a.get("bufferView"), "bufferView index", 0, len(views) - 1)]
            if type(view.get("buffer")) is not int or view["buffer"] != 0 or view.get("extensions"):
                raise ValueError("accessor requires embedded buffer zero")
            start = _integer(view.get("byteOffset", 0), "view offset", 0, len(binary))
            length = _integer(view.get("byteLength"), "view length", 1, len(binary) - start)
            offset = _integer(a.get("byteOffset", 0), "accessor offset", 0, length)
            code, size = {5126: ("f", 4), 5123: ("H", 2), 5121: ("B", 1)}[a["componentType"]]
            stride = _integer(view.get("byteStride", width * size), "stride", width * size, 252)
            if stride % size or (start + offset) % size or offset + (count - 1) * stride + width * size > length:
                raise ValueError("accessor exceeds or misaligns its buffer view")
            rows = [list(struct.unpack_from("<" + code * width, binary, start + offset + i * stride)) for i in range(count)]
            if a.get("normalized", False):
                divisor = 255 if size == 1 else 65535
                rows = [[v / divisor for v in row] for row in rows]
            if any(not math.isfinite(v) for row in rows for v in row):
                raise ValueError("nonfinite accessor data")
            cache[ref] = rows
            return rows

        nodes = _array(document, "nodes", 2048)
        if not nodes:
            raise ValueError("asset requires nodes")
        self._nodes, self._parents = [], [None] * len(nodes)
        for i, node in enumerate(nodes):
            if node.get("extensions") or "weights" in node:
                raise ValueError("node extensions and morph weights are unsupported")
            if not isinstance(node.get("name", ""), str):
                raise ValueError("node name must be text")
            local = {p: _vector(node.get(p, default), len(default), p) for p, default in DEFAULTS.items()}
            local["rotation"] = _quaternion(local["rotation"])
            if "matrix" in node:
                if any(p in node for p in DEFAULTS):
                    raise ValueError("node cannot combine matrix and TRS")
                local["matrix"] = _matrix(node["matrix"])
            self._nodes.append({"name": node.get("name", f"node-{i}"), **local})
            children = node.get("children", [])
            if not isinstance(children, list) or len(children) > len(nodes):
                raise ValueError("invalid node children")
            for child in children:
                child = _integer(child, "child index", 0, len(nodes) - 1)
                if child == i or self._parents[child] is not None:
                    raise ValueError("node hierarchy must have unique parents and no self-cycles")
                self._parents[child] = i
        self._order = [i for i, parent in enumerate(self._parents) if parent is None]
        for parent in self._order:
            self._order.extend(nodes[parent].get("children", []))
        if len(self._order) != len(nodes):
            raise ValueError("cyclic node hierarchy")

        self._clips = {}
        for animation in _array(document, "animations", 128):
            if animation.get("extensions"):
                raise ValueError("animation extensions are unsupported")
            name = animation.get("name")
            if not isinstance(name, str) or not name or name in self._clips:
                raise ValueError("animation names must be nonempty and unique")
            samplers = _array(animation, "samplers", 6144)
            tracks, targets, duration = [], set(), 0.
            for channel in _array(animation, "channels", 6144):
                target = channel.get("target", {})
                if not isinstance(target, dict):
                    raise ValueError("animation target must be an object")
                node = _integer(target.get("node"), "target node", 0, len(nodes) - 1)
                path = target.get("path")
                if path not in DEFAULTS or "matrix" in self._nodes[node] or target.get("extensions") or channel.get("extensions"):
                    raise ValueError("animation requires supported TRS target without matrix or extensions")
                if (node, path) in targets:
                    raise ValueError("duplicate animation channel target")
                targets.add((node, path))
                sampler = samplers[_integer(channel.get("sampler"), "sampler index", 0, len(samplers) - 1)]
                mode = sampler.get("interpolation", "LINEAR")
                if mode not in ("LINEAR", "STEP") or sampler.get("extensions"):
                    raise ValueError("only LINEAR and STEP animation interpolation is supported")
                times = [r[0] for r in accessor(sampler.get("input"), "SCALAR")]
                if times[0] < 0 or times[-1] > 600 or any(b <= a for a, b in zip(times, times[1:])):
                    raise ValueError("key times must strictly increase within 0..600 seconds")
                values = accessor(sampler.get("output"), "VEC4" if path == "rotation" else "VEC3")
                if len(values) != len(times):
                    raise ValueError("animation input/output counts differ")
                if path == "rotation":
                    values = [_quaternion(row) for row in values]
                tracks.append({"node": node, "path": path, "times": times, "values": values, "mode": mode})
                duration = max(duration, times[-1])
            if not tracks or duration <= 0:
                raise ValueError("animation requires nonempty tracks and positive duration")
            self._clips[name] = {"start_s": min(t["times"][0] for t in tracks), "duration_s": duration, "tracks": tracks}

        self._skins = []
        for skin in _array(document, "skins", 128):
            if skin.get("extensions"):
                raise ValueError("skin extensions are unsupported")
            joints = skin.get("joints")
            if not isinstance(joints, list) or not 1 <= len(joints) <= 2048:
                raise ValueError("skin requires bounded joints")
            joints = [_integer(j, "joint", 0, len(nodes) - 1) for j in joints]
            if len(set(joints)) != len(joints):
                raise ValueError("duplicate skin joints")
            inverses = ([_matrix(v) for v in accessor(skin["inverseBindMatrices"], "MAT4")]
                        if "inverseBindMatrices" in skin else [list(IDENTITY) for _ in joints])
            if len(inverses) != len(joints):
                raise ValueError("inverse bind count differs from joint count")
            self._skins.append({"joints": joints, "inverses": inverses})

        self._meshes = []
        instantiated_vertices = 0
        meshes = _array(document, "meshes", 2048)
        for node_index, node in enumerate(nodes):
            if "skin" in node and "mesh" not in node:
                raise ValueError("skin requires mesh")
            if "mesh" not in node:
                continue
            mesh = meshes[_integer(node["mesh"], "mesh index", 0, len(meshes) - 1)]
            skin_index = _integer(node["skin"], "skin index", 0, len(self._skins) - 1) if "skin" in node else None
            for primitive_index, primitive in enumerate(_array(mesh, "primitives", 1024)):
                if primitive.get("targets") or primitive.get("extensions"):
                    raise ValueError("morph targets and compressed/extended geometry are unsupported")
                attributes = primitive.get("attributes", {})
                if not isinstance(attributes, dict):
                    raise ValueError("primitive attributes must be an object")
                positions = accessor(attributes.get("POSITION"), "VEC3")
                instantiated_vertices += len(positions)
                if instantiated_vertices > MAX_VERTICES:
                    raise ValueError("instantiated vertex budget exceeded")
                joint_rows, weight_rows = None, None
                if skin_index is not None:
                    if any(k.startswith(("JOINTS_", "WEIGHTS_")) and k not in ("JOINTS_0", "WEIGHTS_0") for k in attributes):
                        raise ValueError("only four skin influences per vertex are supported")
                    joint_rows = accessor(attributes.get("JOINTS_0"), "VEC4", (5121, 5123))
                    weight_rows = accessor(attributes.get("WEIGHTS_0"), "VEC4", (5126, 5121, 5123))
                    ja, wa = accessors[attributes["JOINTS_0"]], accessors[attributes["WEIGHTS_0"]]
                    if ja.get("normalized", False) or (wa["componentType"] != 5126 and not wa.get("normalized", False)):
                        raise ValueError("invalid joint/weight normalization")
                    if len(joint_rows) != len(positions) or len(weight_rows) != len(positions):
                        raise ValueError("skin attribute counts differ")
                    for joints, weights in zip(joint_rows, weight_rows):
                        if any(not 0 <= j < len(self._skins[skin_index]["joints"]) for j in joints):
                            raise ValueError("vertex references missing joint")
                        if any(w < 0 or w > 1 for w in weights) or abs(sum(weights) - 1) > .02:
                            raise ValueError("skin weights must be nonnegative and sum to one within quantization tolerance")
                    weight_rows = [[w / sum(row) for w in row] for row in weight_rows]
                self._meshes.append({"node": node_index, "primitive": primitive_index, "skin": skin_index,
                                     "positions": positions, "joints": joint_rows, "weights": weight_rows})

    def describe(self):
        return {"schema": "axm.game-pose-asset/v0.1", "source_sha256": self.source_sha256,
                "nodes": [{"index": i, "name": row["name"], "parent": self._parents[i]} for i, row in enumerate(self._nodes)],
                "clips": [{"name": name, "start_s": clip["start_s"], "duration_s": clip["duration_s"],
                           "channels": len(clip["tracks"])} for name, clip in self._clips.items()],
                "skins": [{"joints": list(skin["joints"])} for skin in self._skins],
                "primitives": len(self._meshes), "vertices": sum(len(m["positions"]) for m in self._meshes),
                "truth": game_pose_runtime_catalog()["truth"]}

    def _local(self, clip, time_s, loop):
        time_s = _number(time_s, "time_s")
        if time_s < 0 or type(loop) is not bool:
            raise ValueError("time must be nonnegative and loop boolean")
        local = copy.deepcopy(self._nodes)
        if clip is None:
            return local, 0.
        if not isinstance(clip, str) or clip not in self._clips:
            raise ValueError("unknown animation clip")
        animation = self._clips[clip]
        time_s = time_s % animation["duration_s"] if loop else min(time_s, animation["duration_s"])
        for track in animation["tracks"]:
            times, values = track["times"], track["values"]
            upper = bisect.bisect_right(times, time_s)
            if upper == 0:
                value = list(values[0])
            elif upper == len(times) or track["mode"] == "STEP":
                value = list(values[upper - 1])
            else:
                weight = (time_s - times[upper - 1]) / (times[upper] - times[upper - 1])
                a, b = values[upper - 1], values[upper]
                value = _slerp(a, b, weight) if track["path"] == "rotation" else [x + (y-x)*weight for x, y in zip(a, b)]
            local[track["node"]][track["path"]] = value
        return local, time_s

    def sample(self, clip=None, time_s=0., *, loop=False, blend=None, vertices=False):
        """Blend is an explicit source pose and target weight, not a hidden clock.

        {'clip': source_name, 'time_s': source_time, 'loop': bool, 'weight': 0..1}
        Weight zero returns source; weight one returns the requested target.
        """
        if type(vertices) is not bool:
            raise ValueError("vertices must be boolean")
        local, time_s = self._local(clip, time_s, loop)
        if blend is not None:
            if not isinstance(blend, dict) or set(blend) != {"clip", "time_s", "loop", "weight"}:
                raise ValueError("blend requires exactly clip, time_s, loop and weight")
            weight = _number(blend["weight"], "blend.weight")
            if not 0 <= weight <= 1:
                raise ValueError("blend weight must be in 0..1")
            prior, _ = self._local(blend["clip"], blend["time_s"], blend["loop"])
            for source, target in zip(prior, local):
                for path in DEFAULTS:
                    target[path] = (_slerp(source[path], target[path], weight) if path == "rotation" else
                                    [a + (b-a)*weight for a, b in zip(source[path], target[path])])
        world = [None] * len(local)
        for index in self._order:
            matrix = local[index].get("matrix", None)
            matrix = list(matrix) if matrix is not None else _trs(local[index])
            parent = self._parents[index]
            world[index] = matrix if parent is None else _multiply(world[parent], matrix)
            if any(not math.isfinite(v) for v in world[index]):
                raise ValueError("world transform overflow")
        palettes = [[_multiply(world[j], inverse) for j, inverse in zip(skin["joints"], skin["inverses"])] for skin in self._skins]
        if any(not math.isfinite(v) for palette in palettes for matrix in palette for v in matrix):
            raise ValueError("skin transform overflow")
        result = {"schema": "axm.game-pose-sample/v0.1", "source_sha256": self.source_sha256,
                  "clip": clip, "time_s": time_s, "blend": copy.deepcopy(blend),
                  "local": local, "world_matrices": world, "skin_world_matrices": palettes,
                  "matrix_convention": "row-major, column vectors, scene-space; authored root already included"}
        if vertices:
            deformed = []
            for mesh in self._meshes:
                if mesh["skin"] is None:
                    positions = [_transform(world[mesh["node"]], p) for p in mesh["positions"]]
                else:
                    palette = palettes[mesh["skin"]]
                    positions = []
                    for p, joints, weights in zip(mesh["positions"], mesh["joints"], mesh["weights"]):
                        points = [_transform(palette[j], p) for j in joints]
                        positions.append([sum(points[k][axis] * weights[k] for k in range(4)) for axis in range(3)])
                deformed.append({"node": mesh["node"], "primitive": mesh["primitive"], "positions": positions})
                if any(not math.isfinite(v) for p in positions for v in p):
                    raise ValueError("skin position overflow")
            result["meshes"] = deformed
        return result

    def point(self, pose, node, position=(0., 0., 0.)):
        if pose.get("source_sha256") != self.source_sha256:
            raise ValueError("pose belongs to another source")
        node = _integer(node, "node index", 0, len(self._nodes) - 1)
        return _transform(pose["world_matrices"][node], _vector(position, 3, "point"))


def load_game_pose_glb(path):
    with Path(path).open("rb") as handle:
        body = handle.read(MAX_BYTES + 1)
    return GamePoseAsset(body)


def publish_game_pose(path, asset_path, request):
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    if not isinstance(request, dict) or set(request) - {"clip", "time_s", "loop", "blend", "vertices"}:
        raise ValueError("pose request has unsupported fields")
    asset = load_game_pose_glb(asset_path)
    result = asset.sample(**request)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".axm-pose-", dir=target.parent))
    try:
        atomic_write_json(stage / "pose.json", result)
        atomic_write_json(stage / "asset.json", asset.describe())
        atomic_write_json(stage / "request.json", request)
        if target.exists():
            raise FileExistsError(f"refusing to overwrite existing path: {target}")
        stage.rename(target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return result
