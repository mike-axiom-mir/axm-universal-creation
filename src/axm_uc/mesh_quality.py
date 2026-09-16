"""Independent UV-layout and sampled deformation measurements (stdlib only).

These are explicit geometric policies, not aesthetic or anatomical judgments.
UV overlap is measured continuously; padding is the distance between islands.
Deformation sampling includes every authored key and bounded subdivisions.
"""
from __future__ import annotations

import hashlib
import math

from .game_pose_runtime import GamePoseAsset, _parse
from .software_glb_preview import _accessor


def number(value, label, low, high, integer=False):
    if (type(value) not in ((int,) if integer else (int, float))
            or not math.isfinite(value) or not low <= value <= high):
        raise ValueError(f"{label} must be {'an integer' if integer else 'finite'} in {low}..{high}")
    return value


def _cross2(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _area(poly):
    return abs(sum(p[0]*q[1]-q[0]*p[1] for p, q in zip(poly, poly[1:]+poly[:1])))/2


def _intersection(a, b):
    """Sutherland-Hodgman intersection area of two convex triangles."""
    poly = list(a)
    sign = 1 if _cross2(*b) > 0 else -1
    for p, q in zip(b, b[1:]+b[:1]):
        clipped = []
        for s, e in zip(poly, poly[1:]+poly[:1]):
            ds, de = sign*_cross2(p, q, s), sign*_cross2(p, q, e)
            if (ds >= 0) != (de >= 0):
                t = ds/(ds-de)
                clipped.append([s[k]+t*(e[k]-s[k]) for k in range(2)])
            if de >= 0:
                clipped.append(e)
        poly = clipped
        if not poly:
            return 0.
    return _area(poly)


def _point_segment(p, a, b):
    length = sum((b[k]-a[k])**2 for k in range(2))
    t = max(0., min(1., sum((p[k]-a[k])*(b[k]-a[k]) for k in range(2))/length)) if length else 0
    return math.dist(p, [a[k]+t*(b[k]-a[k]) for k in range(2)])


def _segment_distance(a, b, c, d):
    # Include interior crossings; endpoint distances alone miss these.
    if _cross2(a,b,c)*_cross2(a,b,d) < 0 and _cross2(c,d,a)*_cross2(c,d,b) < 0:
        return 0.
    return min(_point_segment(a,c,d), _point_segment(b,c,d), _point_segment(c,a,b), _point_segment(d,a,b))


def inspect_uv_layout(specification, resolution, padding_px):
    number(resolution, "resolution", 16, 2048, True)
    number(padding_px, "padding_px", 0, resolution/8)
    groups, total_pairs = [], 0
    for group in specification["primitives"]:
        uv, indices, points = group["texcoords"], group["indices"], group["positions"]
        if len(indices)//3 > 4096:
            raise ValueError("UV inspection supports at most 4096 triangles per material")
        triangles = [[uv[i] for i in indices[j:j+3]] for j in range(0,len(indices),3)]
        if any(len(p) != 2 or any(not math.isfinite(v) for v in p) for p in uv):
            raise ValueError("UV coordinates must be finite pairs")
        parent = list(range(len(triangles)))
        def root(i):
            while i != parent[i]:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        edges = {}
        for face in range(len(triangles)):
            ids = indices[face*3:face*3+3]
            for a,b in zip(ids, ids[1:]+ids[:1]):
                key = tuple(sorted((tuple(round(v,7) for v in [*points[i],*uv[i]]) for i in (a,b))))
                if key in edges:
                    parent[root(face)] = root(edges[key][0])
                edges.setdefault(key, []).append(face)
        boundary = []
        for key, faces in edges.items():
            if len(faces) == 1:
                boundary.append((root(faces[0]), key[0][-2:], key[1][-2:]))
        bounds = [(min(p[0] for p in t), min(p[1] for p in t), max(p[0] for p in t), max(p[1] for p in t)) for t in triangles]
        overlaps, overlap_area = 0, 0.
        order = sorted(range(len(bounds)), key=lambda i: bounds[i][0])
        for at,i in enumerate(order):
            a = bounds[i]
            for j in order[at+1:]:
                b = bounds[j]
                if b[0] >= a[2]-1e-10:
                    break
                if b[1] >= a[3]-1e-10 or b[3] <= a[1]+1e-10:
                    continue
                total_pairs += 1
                if total_pairs > 2_000_000:
                    raise ValueError("UV pair-work budget exceeded")
                area = _intersection(triangles[i], triangles[j])
                if area > 1e-10:
                    overlaps += 1
                    overlap_area += area
        border = min(min(p[0],p[1],1-p[0],1-p[1]) for p in uv)*resolution
        # Only distances below the requested padding affect the policy. This
        # makes the broad-phase bounded measurement useful for large layouts.
        nearest = padding_px/resolution
        boundary.sort(key=lambda edge:min(edge[1][0],edge[2][0]))
        for i,(island,a,b) in enumerate(boundary):
            for other,c,d in boundary[i+1:]:
                if min(c[0],d[0]) > max(a[0],b[0])+nearest:
                    break
                if island == other:
                    continue
                if any(max(a[k],b[k])+nearest < min(c[k],d[k]) or max(c[k],d[k])+nearest < min(a[k],b[k]) for k in range(2)):
                    continue
                total_pairs += 1
                if total_pairs > 2_000_000:
                    raise ValueError("UV pair-work budget exceeded")
                nearest = min(nearest, _segment_distance(a,b,c,d))
        collapsed = sum(_area(t) <= 1e-12 for t in triangles)
        checks = {"noncollapsed": collapsed == 0, "no_positive_area_overlap": overlaps == 0,
                  "atlas_border_padding": border+1e-4 >= padding_px,
                  "island_padding": nearest*resolution+1e-4 >= padding_px}
        groups.append({"id": group["id"], "triangles": len(triangles), "islands": len({root(i) for i in parent}),
                       "overlapping_pairs": overlaps, "overlap_area_uv": overlap_area, "collapsed_triangles": collapsed,
                       "used_area_fraction": sum(_area(t) for t in triangles), "border_padding_px": border,
                       "island_padding_px_capped_at_requirement": nearest*resolution, "checks": checks})
    return {"schema": "axm.uv-layout-quality/v1", "status": "PASS" if groups and all(all(g["checks"].values()) for g in groups) else "FAIL",
            "resolution": resolution, "required_padding_px": padding_px, "groups": groups,
            "scope": "One unique 0..1 atlas per material. Geometric overlap and base-level padding; no UDIM or all-mip guarantee."}


def _area3(a,b,c):
    u,v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
    return math.sqrt(sum(x*x for x in (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])))/2


def inspect_deformation(body, policy=None):
    policy = {} if policy is None else policy
    defaults = {"samples_per_interval": 4, "minimum_area_ratio": .05, "maximum_edge_ratio": 3.,
                "loop_clips": [], "maximum_loop_delta_m": .001, "contacts": [], "require_skin": True}
    if not isinstance(policy, dict) or set(policy)-defaults.keys():
        raise ValueError("unsupported deformation policy")
    policy = {**defaults, **policy}
    subdivisions = number(policy["samples_per_interval"], "samples_per_interval", 1, 32, True)
    number(policy["minimum_area_ratio"], "minimum_area_ratio", 0.0001, 1)
    number(policy["maximum_edge_ratio"], "maximum_edge_ratio", 1, 100)
    number(policy["maximum_loop_delta_m"], "maximum_loop_delta_m", 0, 10)
    if type(policy["require_skin"]) is not bool or not isinstance(policy["loop_clips"],list) or not isinstance(policy["contacts"],list) or len(policy["contacts"]) > 64:
        raise ValueError("invalid deformation policy lists/skin requirement")
    asset = GamePoseAsset(body)
    description = asset.describe()
    names = {c["name"] for c in description["clips"]}
    if set(policy["loop_clips"])-names:
        raise ValueError("loop_clips names missing clips")
    doc,binary = _parse(body)
    rest = asset.sample(vertices=True)["meshes"]
    topology = []
    for mesh in rest:
        primitive = doc["meshes"][doc["nodes"][mesh["node"]]["mesh"]]["primitives"][mesh["primitive"]]
        if primitive.get("mode",4) != 4:
            raise ValueError("deformation inspection requires triangle primitives")
        ids = [int(r[0]) for r in _accessor(doc,binary,primitive["indices"])] if "indices" in primitive else list(range(len(mesh["positions"])))
        if len(ids)%3 or any(i < 0 or i >= len(mesh["positions"]) for i in ids):
            raise ValueError("invalid deformation triangle indices")
        triangles = [ids[i:i+3] for i in range(0,len(ids),3)]
        areas = [_area3(*(mesh["positions"][v] for v in tri)) for tri in triangles]
        edges = sorted({tuple(sorted((a,b))) for tri in triangles for a,b in zip(tri,tri[1:]+tri[:1])})
        lengths = [math.dist(mesh["positions"][a],mesh["positions"][b]) for a,b in edges]
        if any(a < 1e-12 for a in areas) or any(d < 1e-10 for d in lengths):
            raise ValueError("rest geometry contains collapsed triangles/edges")
        topology.append((triangles,areas,edges,lengths))
    contacts = []
    for c in policy["contacts"]:
        if not isinstance(c,dict) or set(c) != {"clip","mesh","vertex","start_s","end_s","maximum_drift_m"} or c["clip"] not in names:
            raise ValueError("contact requires clip, mesh, vertex, start_s, end_s, maximum_drift_m")
        mi = number(c["mesh"],"contact mesh",0,len(rest)-1,True)
        number(c["vertex"],"contact vertex",0,len(rest[mi]["positions"])-1,True)
        duration = next(r["duration_s"] for r in description["clips"] if r["name"] == c["clip"])
        number(c["start_s"],"contact start",0,duration)
        number(c["end_s"],"contact end",c["start_s"],duration)
        number(c["maximum_drift_m"],"contact drift",0,100)
        contacts.append(c)
    clips, work = [], 0
    for clip in description["clips"]:
        # The validated runtime exposes exact authored tracks; use their key
        # times so a narrow failure at an authored extreme cannot be skipped.
        keys = sorted({0.,clip["duration_s"], *(t for tr in asset._clips[clip["name"]]["tracks"] for t in tr["times"]),
                       *(t for c in contacts if c["clip"] == clip["name"] for t in (c["start_s"],c["end_s"]))})
        times = sorted({keys[-1], *(a+(b-a)*i/subdivisions for a,b in zip(keys,keys[1:]) for i in range(subdivisions))})
        work += len(times)*description["vertices"]
        if len(times) > 1024 or work > 4_000_000:
            raise ValueError("deformation sampling work budget exceeded")
        min_area,max_edge,max_motion = float("inf"),0.,0.
        first,last = None,None
        contact_rows = [{**c,"observed_maximum_drift_m":0.,"reference":None} for c in contacts if c["clip"] == clip["name"]]
        for time in times:
            meshes = asset.sample(clip["name"],time,vertices=True)["meshes"]
            first = meshes if first is None else first
            last = meshes
            for reference,mesh,top in zip(rest,meshes,topology):
                points = mesh["positions"]
                triangles,areas,edges,lengths = top
                min_area = min(min_area, *(_area3(*(points[v] for v in tri))/a for tri,a in zip(triangles,areas)))
                max_edge = max(max_edge, *(math.dist(points[a],points[b])/d for (a,b),d in zip(edges,lengths)))
                max_motion = max(max_motion, *(math.dist(a,b) for a,b in zip(reference["positions"],points)))
            for c in contact_rows:
                if c["start_s"] <= time <= c["end_s"]:
                    point = meshes[c["mesh"]]["positions"][c["vertex"]]
                    c["reference"] = point if c["reference"] is None else c["reference"]
                    c["observed_maximum_drift_m"] = max(c["observed_maximum_drift_m"],math.dist(point,c["reference"]))
        endpoint = max(math.dist(a,b) for m,n in zip(first,last) for a,b in zip(m["positions"],n["positions"]))
        checks = {"no_sampled_collapse":min_area >= policy["minimum_area_ratio"],
                  "bounded_sampled_stretch":max_edge <= policy["maximum_edge_ratio"],
                  "declared_loop_continuity":clip["name"] not in policy["loop_clips"] or endpoint <= policy["maximum_loop_delta_m"],
                  "declared_contacts":all(c["observed_maximum_drift_m"] <= c["maximum_drift_m"] for c in contact_rows)}
        clips.append({"clip":clip["name"],"times_s":times,"minimum_area_ratio":min_area,"maximum_edge_ratio":max_edge,
                      "maximum_motion_m":max_motion,"endpoint_delta_m":endpoint,"contacts":contact_rows,"checks":checks})
    checks = [{"type":"animated-mesh-present","passed":bool(clips and rest)},
              {"type":"required-skin-present","passed":bool(description["skins"]) or not policy["require_skin"]},
              {"type":"sampled-deformation-policy","passed":bool(clips) and all(all(r["checks"].values()) for r in clips)}]
    return {"schema":"axm.deformation-quality/v1","artifact_sha256":hashlib.sha256(body).hexdigest(),
            "status":"PASS" if all(c["passed"] for c in checks) else "FAIL","checks":checks,"policy":policy,"clips":clips,
            "scope":"Authored keys and subdivisions, skin weights/hierarchy, triangle area, edge stretch, declared contacts and loops. No unsampled extrema, self-intersection, anatomy or motion-quality proof."}
