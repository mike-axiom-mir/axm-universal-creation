import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('mesh_profiles',Path(__file__).resolve().parents[1]/'tools/blender/axm_mesh_profiles.py')
profiles=importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)


class MeshProfileTests(unittest.TestCase):
    def test_thin_panels_remain_strictly_convex_and_inside_bounds(self):
        # The actual failing service-frame dimensions plus tall/wide variants.
        for w,d,c in [(3.8,.13,.16),(.13,3.8,.16),(12,1.7,.35),(.01,.01,5),(.18,.58,.045)]:
            with self.subTest(w=w,d=d,c=c):
                poly=profiles.octagon(w,d,c)
                self.assertEqual(len(set(poly)),8)
                for x,y in poly:
                    self.assertLessEqual(abs(x),w/2)
                    self.assertLessEqual(abs(y),d/2)
                for i in range(8):
                    a,b,c=poly[i],poly[(i+1)%8],poly[(i+2)%8]
                    cross=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
                    self.assertGreater(cross,0)

    def test_invalid_dimensions_rejected(self):
        for args in [(0,1,.1),(1,-1,.1),(1,1,float('nan')),(1,1,0)]:
            with self.assertRaises(ValueError): profiles.octagon(*args)
