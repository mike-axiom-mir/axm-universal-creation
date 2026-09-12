import json, math, unittest
from xml.etree import ElementTree
from axm_uc.format_templates import catalog, resolve_format, layout_project
from axm_uc.template import render_project_template

class FormatTests(unittest.TestCase):
    def test_print_dimensions_and_screen_pixels(self):
        f=resolve_format('poker-card',bleed=3,safe=3)
        self.assertEqual(f['canvas'],[69.5,94.9])
        self.assertEqual(f['trim'],[3,3,63.5,88.9])
        self.assertEqual(f['safe'],[6,6,57.5,82.9])
        self.assertEqual(f['raster_pixels'],[821,1121])
        self.assertEqual(resolve_format('full-hd',dpi=600)['raster_pixels'],[1920,1080])
        self.assertEqual(resolve_format('a4',landscape=True)['canvas'],[297,210])

    def test_invalid_dimensions(self):
        for args in ({'dpi':True},{'dpi':math.nan},{'bleed':-1},{'safe':100},{'landscape':1}):
            with self.subTest(args=args),self.assertRaises(ValueError):resolve_format('poker-card',**args)
        with self.assertRaises(ValueError):resolve_format('hd',bleed=3)

    def test_all_layouts_fit_and_escape(self):
        for name in catalog()['formats']:
            for layout in catalog()['layouts']:
                project=layout_project(name,layout,'<Test & title>')
                rendered=render_project_template(project,{})
                ElementTree.fromstring(rendered['files']['layout.svg'])
                m=json.loads(rendered['files']['layout.json']);w,h=m['format']['canvas']
                for x,y,rw,rh in m['regions'].values():
                    self.assertGreater(rw,0);self.assertGreater(rh,0)
                    self.assertLessEqual(x+rw,w+1e-8);self.assertLessEqual(y+rh,h+1e-8)
        c=catalog();c['layouts']['poster'].clear()
        self.assertTrue(catalog()['layouts']['poster'])
