"""Stateless performance evaluation at caller-owned time, with decoded mesh checks."""
from __future__ import annotations

import math

from .character_motion import build_character_motion, number, require
from .character_performance import sample_performance
from .character_recipe import compile_character_recipe
from .game_pose_runtime import GamePoseAsset
from .mesh_quality import _area3


class CharacterController:
    """An explicit recipe owns the body; elapsed seconds own the simulation clock."""

    def __init__(self, recipe):
        self.compiled = compile_character_recipe(recipe)
        performance = self.compiled['performance']
        require(performance is not None, 'runtime controller requires a performance recipe')
        self.plans = {p['name']: p for p in performance['controllers']}
        self.landmarks = performance['landmarks']
        self.built = build_character_motion(self.compiled['specification'], self.compiled['motion'])
        self.asset = GamePoseAsset(self.built['body'])
        document = self.built['document']
        self.joint_nodes = {j['id']: node for j, node in
                            zip(self.compiled['motion']['joints'], document['skins'][0]['joints'])}
        self.part_nodes = {n['name']: i for i, n in enumerate(document['nodes']) if 'mesh' in n}

    def sample(self, clip, elapsed_s, *, vertices=False):
        require(isinstance(clip, str) and clip in self.plans, 'unknown performance clip')
        elapsed_s = number(elapsed_s)
        require(elapsed_s >= 0, 'elapsed time cannot be negative')
        plan = self.plans[clip]
        values, observations = sample_performance(plan, self.landmarks, elapsed_s/plan['duration'])
        rows = {}
        for (joint, path), value in values.items():
            node = self.joint_nodes[joint]
            rows.setdefault(node, {'node': node})[path] = value
        pose = self.asset.sample(vertices=vertices, overrides=list(rows.values()))
        for row in observations:
            actual = self.asset.point(pose, self.joint_nodes[row['joint']])
            row['target_error_m'] = math.dist(actual, row['target'])
            require(row['target_error_m'] <= 1e-6, 'runtime solve missed its end target')
        pose['performance'] = {'clip': clip, 'elapsed_s': elapsed_s,
                               'phase': elapsed_s/plan['duration'], 'observations': observations,
                               'root_travel_included': True,
                               'boundary': 'IK solved at this query time. Flat declared support paths; no terrain sensing, dynamics or unsampled deformation proof.'}
        return pose

    def measure(self, clip, times, *, feet=None, up_axis=2, ground_height_m=0):
        """Observe queried poses, triangle/edge distortion and declared foot surfaces."""
        require(isinstance(clip, str) and clip in self.plans, 'unknown performance clip')
        require(isinstance(times, list) and 2 <= len(times) <= 1024, 'measurement needs 2..1024 times')
        times = [number(t) for t in times]
        require(times[0] >= 0 and all(a < b for a,b in zip(times,times[1:])), 'measurement times must increase')
        require(type(up_axis) is int and up_axis in (0,1,2), 'invalid measurement up axis')
        ground = number(ground_height_m)
        feet = {} if feet is None else feet
        ends = {c['joints'][-1] for c in self.plans[clip]['chains']}
        require(isinstance(feet, dict) and set(feet) <= ends
                and all(isinstance(p, str) and p in self.part_nodes for p in feet.values()), 'invalid end-joint to foot-part mapping')
        require(len(set(feet.values())) == len(feet), 'each foot part must have one end joint')
        rest = self.asset.sample(vertices=True)['meshes']
        spec = self.compiled['specification']
        require(len(times)*sum(len(p['positions']) + len(p['indices']) for p in spec['primitives']) <= 4_000_000,
                'controller measurement work budget exceeded')
        topology = []
        for part, mesh in zip(spec['primitives'], rest):
            indices, points = part['indices'], mesh['positions']
            triangles = [indices[i:i+3] for i in range(0,len(indices),3)]
            areas = [_area3(*(points[v] for v in tri)) for tri in triangles]
            edges = sorted({tuple(sorted((a,b))) for tri in triangles for a,b in zip(tri,tri[1:]+tri[:1])})
            lengths = [math.dist(points[a],points[b]) for a,b in edges]
            require(all(a > 1e-12 for a in areas) and all(d > 1e-10 for d in lengths), 'collapsed rest geometry')
            topology.append((triangles,areas,edges,lengths))
        metrics = {'maximum_target_error_m': 0., 'maximum_bend_degrees': 0.,
                   'minimum_area_ratio': float('inf'), 'maximum_edge_ratio': 0.}
        if feet:
            metrics.update(maximum_contact_slip_m=0., foot_penetration_m=0.)
        reference, compared, peaks, contacts = {}, set(), {joint: None for joint in feet}, 0
        for time in times:
            pose = self.sample(clip, time, vertices=True)
            meshes = {m['node']: m for m in pose['meshes']}
            for mesh, top in zip(pose['meshes'], topology):
                points = mesh['positions']
                triangles, areas, edges, lengths = top
                metrics['minimum_area_ratio'] = min(metrics['minimum_area_ratio'],
                    *(_area3(*(points[v] for v in tri))/a for tri,a in zip(triangles,areas)))
                metrics['maximum_edge_ratio'] = max(metrics['maximum_edge_ratio'],
                    *(math.dist(points[a],points[b])/d for (a,b),d in zip(edges,lengths)))
            for row in pose['performance']['observations']:
                metrics['maximum_target_error_m'] = max(metrics['maximum_target_error_m'], row['target_error_m'])
                metrics['maximum_bend_degrees'] = max(metrics['maximum_bend_degrees'], row['bend_degrees'])
                joint = row['joint']
                if joint not in feet:
                    continue
                points = meshes[self.part_nodes[feet[joint]]]['positions']
                height = min(p[up_axis] for p in points) - ground
                metrics['foot_penetration_m'] = max(metrics['foot_penetration_m'], -height)
                if row['contact']:
                    contacts += 1
                    if (joint,row['plant']) in reference:
                        compared.add(joint)
                    first = reference.setdefault((joint,row['plant']),points)
                    metrics['maximum_contact_slip_m'] = max(metrics['maximum_contact_slip_m'],
                                                            *(math.dist(a,b) for a,b in zip(first,points)))
                else:
                    peaks[joint] = max(height, peaks[joint] if peaks[joint] is not None else height)
        if feet:
            # Missing a swing is missing evidence, not a zero-height successful observation.
            if all(v is not None for v in peaks.values()):
                metrics['peak_foot_lift_m'] = min(peaks.values())
            if compared != set(feet):
                metrics.pop('maximum_contact_slip_m')
        return {'schema': 'axm.character-controller-evidence/v0.1', 'clip': clip, 'times_s': times,
                'source_sha256': self.asset.source_sha256, 'metrics': metrics,
                'contact_samples': contacts, 'foot_parts': feet,
                'boundary': 'Measured at listed times, using decoded GLB vertices. No unsampled extrema, self-intersection, balance, shaded-normal or artistic-quality claim.'}
