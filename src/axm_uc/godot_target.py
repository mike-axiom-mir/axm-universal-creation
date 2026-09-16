"""Actual optional Godot import/render/playback evidence for profession crews.

The fixed worker loads only a validated embedded GLB in a fresh local project.
No downloads, caller scripts, editor projects or cached PASS receipts are used.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import tempfile
import zlib

from .atomic import atomic_write_json
from .game_pose_runtime import GamePoseAsset, _parse
from .mesh_production import _asset, _sha, _target
from .mesh_quality import number
from .native_textures import decode_png, MAX_PNG_BYTES

KINDS = {"validate-godot-target"}
WORKER = Path(__file__).with_name("data") / "engine" / "godot_probe.gd"
PROJECT = '''config_version=5
[application]
config/name="UC isolated target observation"
[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
textures/default_filters/use_nearest_mipmap_filter=false
'''


def godot_executable():
    value = os.environ.get("AXM_GODOT") or shutil.which("godot") or shutil.which("godot4")
    if not value or not Path(value).is_file():
        raise RuntimeError("Godot backend unavailable. Set AXM_GODOT to a Godot 4.4+ executable. Rendering also requires a display/OpenGL context; headless dummy rendering is not evidence.")
    return str(Path(value).resolve())


def target_options(inputs):
    defaults = {"engine": "godot", "width": 640, "height": 480, "pose_samples": 3,
                "views": [{"yaw": .6, "elevation": .35}], "playback": None}
    value = inputs.get("options", {})
    if not isinstance(value, dict) or set(value) - defaults.keys():
        raise ValueError("unsupported Godot target options")
    p = {**defaults, **value}
    if p["engine"] != "godot":
        raise ValueError("Godot evidence cannot certify a different target engine")
    for key in ("width", "height"):
        number(p[key], key, 64, 1024, True)
    number(p["pose_samples"], "pose_samples", 2, 16, True)
    if not isinstance(p["views"], list) or not 1 <= len(p["views"]) <= 8:
        raise ValueError("target requires 1..8 views")
    for row in p["views"]:
        if not isinstance(row, dict) or set(row) - {"yaw", "elevation", "clip", "time_s"}:
            raise ValueError("invalid Godot view")
        number(row.get("yaw"), "yaw", -6.284, 6.284)
        number(row.get("elevation"), "elevation", -.1, 1.45)
        number(row.get("time_s", 0), "time_s", 0, 600)
        if row.get("clip") is not None and (not isinstance(row["clip"], str) or not row["clip"]):
            raise ValueError("clip must name an authored animation")
    playback = p["playback"]
    if playback is not None:
        if not isinstance(playback, dict) or set(playback) != {"clip", "fps", "frames"}:
            raise ValueError("playback requires clip, fps and frames")
        if not isinstance(playback["clip"], str) or not playback["clip"]:
            raise ValueError("playback requires an authored clip")
        number(playback["fps"], "fps", 1, 60, True)
        number(playback["frames"], "frames", 2, 121, True)
        if p["width"] * p["height"] * playback["frames"] > 32_000_000:
            raise ValueError("playback pixel budget exceeded")
    return p


def validate_station(root, kind, inputs):
    if kind not in KINDS or not isinstance(inputs, dict):
        raise ValueError("unknown game-engine target station")
    _target(root, inputs.get("path"))
    _target(root, inputs.get("asset"))
    target_options(inputs)


def _poses(asset, options):
    clips = asset.describe()["clips"]
    poses = [{"clip": None, "time_s": 0.}]
    for clip in clips:
        poses += [{"clip": clip["name"], "time_s": clip["duration_s"] * i / (options["pose_samples"] - 1)}
                  for i in range(options["pose_samples"])]
    if len(poses) > 64:
        raise ValueError("Godot pose budget exceeded")
    for view in options["views"]:
        asset.sample(view.get("clip"), view.get("time_s", 0), vertices=True)
    playback = options["playback"]
    if playback:
        selected = next((c for c in clips if c["name"] == playback["clip"]), None)
        if selected is None or (playback["frames"]-1) / playback["fps"] > selected["duration_s"] + 1e-8:
            raise ValueError("playback must fit the declared authored clip duration")
    return poses


def _bounds(asset, pose):
    meshes = asset.sample(pose.get("clip"), pose.get("time_s", 0), vertices=True)["meshes"]
    points = [point for mesh in meshes for point in mesh["positions"]]
    return {"min": [min(p[k] for p in points) for k in range(3)],
            "max": [max(p[k] for p in points) for k in range(3)]}


def _geometry_checks(asset, poses, actual, triangles):
    if not isinstance(actual, list) or len(actual) != len(poses):
        return [], False
    rows = []
    for pose, row in zip(poses, actual):
        expected = _bounds(asset, pose)
        error = max(abs(expected[key][k] - row["bounds_m"][key][k]) for key in ("min", "max") for k in range(3))
        rows.append({**pose, "bounds_error_m": error, "triangles_match": row["triangles"] == triangles})
    return rows, all(r["bounds_error_m"] < 1e-4 and r["triangles_match"] for r in rows)


def _render_png(body):
    """Validate engine PNG chunks and retain their unchanged RGB scanlines.

    Godot's PNG encoder adds ancillary metadata. UC's native format deliberately
    supports IHDR/IDAT/IEND only. Validate every CRC before removing ancillary
    chunks; unknown critical chunks and malformed data still fail closed.
    """
    if not 45 <= len(body) <= MAX_PNG_BYTES or body[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("invalid bounded engine PNG")
    cursor, parts, removed = 8, [body[:8]], []
    while cursor + 12 <= len(body):
        length = struct.unpack_from(">I", body, cursor)[0]
        kind = body[cursor+4:cursor+8]
        end = cursor + 8 + length
        if end + 4 > len(body) or zlib.crc32(body[cursor+4:end]) & 0xffffffff != struct.unpack_from(">I", body, end)[0]:
            raise ValueError("invalid engine PNG chunk length/CRC")
        if kind in (b"IHDR", b"IDAT", b"IEND"):
            parts.append(body[cursor:end+4])
        elif kind[0] & 32:
            removed.append(kind.decode("ascii"))
        else:
            raise ValueError("unsupported critical engine PNG chunk")
        cursor = end + 4
    if cursor != len(body):
        raise ValueError("truncated engine PNG")
    canonical = b"".join(parts)
    decode_png(canonical)
    return canonical, removed


def _produce(body, p, output, executable):
    asset = GamePoseAsset(body)
    poses = _poses(asset, p)
    doc, _ = _parse(body)
    triangles = sum((doc["accessors"][pr["indices"]]["count"] if "indices" in pr else
                     doc["accessors"][pr["attributes"]["POSITION"]]["count"]) // 3
                    for node in doc["nodes"] if "mesh" in node for pr in doc["meshes"][node["mesh"]]["primitives"])
    # Bound the independent geometry work as well as the subprocess wall time.
    if triangles * (len(poses) + (p["playback"]["frames"] if p["playback"] else 0)) > 2_000_000:
        raise ValueError("Godot sampled geometry budget exceeded")
    output.mkdir(parents=True, exist_ok=False)
    (output / "asset.glb").write_bytes(body)
    (output / "project.godot").write_text(PROJECT, encoding="utf-8")
    shutil.copyfile(WORKER, output / "probe.gd")
    atomic_write_json(output / "request.json", {**p, "poses": poses})
    command = [executable, "--path", str(output), "--rendering-method", "gl_compatibility",
               "--audio-driver", "Dummy", "--resolution", f'{p["width"]}x{p["height"]}',
               "--script", str(output / "probe.gd")]
    report = {"schema": "axm.godot-target/v1", "engine": "godot", "source_sha256": _sha(body),
              "worker_sha256": _sha(WORKER.read_bytes()), "options": p,
              "status": "FAIL", "checks": [], "released": False,
              "visual_quality": "REQUIRES_REVIEW", "professional_acceptance": "NOT_TESTED"}
    try:
        with (output / "worker.log").open("wb") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=240, check=False)
        if result.returncode or not (output / "worker-result.json").is_file():
            raise RuntimeError("Godot did not complete the probe; see worker.log (exit " + str(result.returncode) + ")")
        worker = json.loads((output / "worker-result.json").read_text(encoding="utf-8"))
        if worker.get("error"):
            raise RuntimeError(worker["error"])
        removed = {}
        for image_path in output.glob("*.png"):
            canonical, metadata = _render_png(image_path.read_bytes())
            image_path.write_bytes(canonical)
            removed[image_path.name] = metadata
        report["removed_png_metadata"] = removed
        report["backend"] = worker["backend"]
        geometry, good = _geometry_checks(asset, poses, worker["poses"], triangles)
        report["pose_comparison"] = geometry
        checks = [{"type": "actual-rendering-backend", "passed": worker["backend"]["renderer"] == "gl_compatibility" and worker["backend"]["display"] != "headless"},
                  {"type": "exact-imported-source", "passed": worker["source_sha256"] == _sha(body)},
                  {"type": "native-target-geometry-agreement", "passed": good}]
        expected = {k: 0 for k in ("albedo", "normal", "roughness", "metallic", "ao", "emission")}
        for node in doc["nodes"]:
            if "mesh" not in node:
                continue
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                m = doc.get("materials", [])[primitive["material"]] if "material" in primitive else {}
                pbr = m.get("pbrMetallicRoughness", {})
                for role, present in {"albedo": "baseColorTexture" in pbr, "normal": "normalTexture" in m,
                    "roughness": "metallicRoughnessTexture" in pbr, "metallic": "metallicRoughnessTexture" in pbr,
                    "ao": "occlusionTexture" in m, "emission": "emissiveTexture" in m}.items():
                    expected[role] += present
        imported = worker["material_bindings"]
        report["material_bindings"] = imported
        checks.append({"type": "target-texture-bindings-decoded", "passed": all(sum(bool(m.get(role)) for m in imported) >= count for role, count in expected.items())})
        playback = p["playback"]
        if playback:
            frames = [{"clip": playback["clip"], "time_s": i / playback["fps"]} for i in range(playback["frames"])]
            motion, motion_good = _geometry_checks(asset, frames, worker["playback"], triangles)
            report["playback_comparison"] = motion
            checks.append({"type": "stepped-animation-player-agreement", "passed": motion_good})
        image_names = [f"view-{i:02d}" for i in range(len(p["views"]))]
        if playback:
            image_names += [f"frame-{i:03d}" for i in range(playback["frames"])]
        images = []
        for name in image_names:
            w, h, pixels = decode_png((output / (name + ".png")).read_bytes())
            mw, mh, mask = decode_png((output / (name + "-coverage.png")).read_bytes())
            images.append({"file": name + ".png", "width": w, "height": h,
                           "channel_range": max(pixels)-min(pixels),
                           "visible_pixels": sum(v > 127 for v in mask[::3]),
                           "mask_dimensions_match": (mw, mh) == (w, h)})
        checks.append({"type": "all-target-images-and-asset-masks", "passed": all(r["width"] == p["width"] and r["height"] == p["height"] and r["channel_range"] > 8 and r["visible_pixels"] > 0 and r["mask_dimensions_match"] for r in images)})
        report.update(checks=checks, images=images, status="PASS" if all(c["passed"] for c in checks) else "FAIL")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        report["failure"] = str(exc)
        log_path = output / "worker.log"
        if log_path.exists():
            report["failure_log_tail"] = log_path.read_text(errors="replace")[-6000:]
        report["checks"].append({"type": "worker-completed-with-evidence", "passed": False})
    # Retain the exact input, worker, logs, failed reports and successful frames.
    report["artifacts"] = {f.name: _sha(f.read_bytes()) for f in output.iterdir()
                           if f.is_file() and f.name not in {"report.json", "worker.log", "worker-result.json"}}
    atomic_write_json(output / "report.json", report)
    return report


def run_station(root, kind, inputs):
    validate_station(root, kind, inputs)
    path = _target(root, inputs["path"])
    if path.exists():
        raise FileExistsError("Godot station refuses existing output")
    _, body = _asset(root, inputs["asset"])
    executable = godot_executable()
    p = target_options(inputs)
    with tempfile.TemporaryDirectory(prefix="uc-godot-") as folder:
        generated = Path(folder) / "result"
        report = _produce(body, p, generated, executable)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(generated, path)
    return report


def observe_station(root, kind, inputs):
    validate_station(root, kind, inputs)
    path = _target(root, inputs["path"])
    _, body = _asset(root, inputs["asset"])
    stored = json.loads((path / "report.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="uc-godot-observe-") as folder:
        fresh_path = Path(folder) / "fresh"
        fresh = _produce(body, target_options(inputs), fresh_path, godot_executable())
        checks = [{"type": "fresh-actual-target-pass", "passed": fresh["status"] == "PASS"},
                  {"type": "stored-actual-target-pass", "passed": stored.get("status") == "PASS"}]
        for key in ("schema", "engine", "source_sha256", "worker_sha256", "options", "backend", "checks",
                    "pose_comparison", "playback_comparison", "material_bindings", "images", "released",
                    "visual_quality", "professional_acceptance", "removed_png_metadata"):
            checks.append({"type": "fresh-" + key, "passed": stored.get(key) == fresh.get(key)})
        original_files = stored.get("artifacts", {})
        checks.append({"type": "complete-artifact-set", "passed": set(original_files) == set(fresh["artifacts"])})
        for name, digest in fresh["artifacts"].items():
            target = path / name
            checks.append({"type": "current-artifact-" + name, "passed": target.is_file() and _sha(target.read_bytes()) == original_files.get(name)})
            # Images may differ across graphics driver builds. This observer
            # requires an exact repeat on the recorded backend, not an invented
            # cross-device visual equivalence claim.
            checks.append({"type": "fresh-artifact-" + name, "passed": original_files.get(name) == digest})
    return {"status": "PASS" if checks and all(c["passed"] for c in checks) else "FAIL", "checks": checks,
            "failure": fresh.get("failure"), "failure_log_tail": fresh.get("failure_log_tail"),
            "scope": "Actual Godot import, decoded texture bindings, posed geometry, rendered masks and optional stepped animation. No gameplay, device-performance or artistic acceptance.",
            "visual_quality": "REQUIRES_REVIEW", "professional_acceptance": "NOT_TESTED"}
