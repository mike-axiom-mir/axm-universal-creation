"""Original salvage-panel effect recipe, using the recovered Studio compositor.

Run with Python + local Node, no browser, Pillow, network or AI dependency.
Writes a fresh project directory; repeat into another directory to verify replay.
"""
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from axm_uc.fabric_noise import png_bytes
from axm_uc.studio_compositor import SCHEMA, compose_studio_project, publish_studio_project


def segment_distance(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)


def build(destination):
    root = Path(destination)
    if root.exists(): raise FileExistsError(root)
    root.mkdir(parents=True)
    size = 384
    panel, spark, protection, paint = bytearray(), bytearray(), bytearray(), bytearray()
    paths = [[(75,72),(152,97),(129,150),(226,121),(190,187),(303,205),(250,288),(317,328)],
             [(129,150),(78,179),(93,218),(49,254)],[(226,121),(263,75),(325,87)],
             [(190,187),(184,231),(219,256)]]
    segments = [(a,b) for path in paths for a,b in zip(path,path[1:])]
    letters = {'A':['01110','11011','11011','11111','11011','11011','11011'],
               'X':['11011','11011','01110','00100','01110','11011','11011'],
               'M':['10001','11011','11111','10101','10001','10001','10001']}
    for y in range(size):
        for x in range(size):
            grain = ((x*73+y*131+(x*y)%53)%19)-9
            rim = min(x,y,size-1-x,size-1-y)
            rgb = [38+grain,49+grain,61+grain]
            if rim < 10: rgb = [12,19,28]
            elif rim < 17: rgb = [103+grain,116+grain,125+grain]
            elif rim < 24: rgb = [23,30,37]
            if 34 < x < 350 and (34 < y < 54 or 330 < y < 350):
                rgb = [192+grain,124+grain,36] if (x+y)//19%2 else [32,33,31]
            # Authored rivets, slotted vents, scratched finish and bolted nameplate.
            for bx,by in ((32,32),(352,32),(32,352),(352,352)):
                d=math.hypot(x-bx,y-by)
                if d<8: rgb=[125+grain,137+grain,145+grain] if d<6 else [13,19,25]
                if d<5 and abs(x-bx-y+by)<2: rgb=[14,23,31]
            if 267<x<335 and 237<y<300 and y%12<5: rgb=[12,18,25]
            if 115<x<256 and 245<y<310:
                rgb=[194+grain,184+grain,152+grain] if 119<x<252 and 249<y<306 else [16,25,34]
                lx, ly = (x-132)//6, (y-258)//6
                if 0 <= ly < 7 and 0 <= lx < 17:
                    letter, col = lx//6, lx%6
                    if letter<3 and col<5 and letters['AXM'[letter]][ly][col]=='1': rgb=[25,36,42]
            elif ((x*17+y*43)%1301<3) and rim>25: rgb=[135,145,142]
            panel.extend([*rgb,255])
            d=min(segment_distance(x,y,a,b) for a,b in segments)
            rgb=[130,245,255] if d<1 else [15,153,235] if d<2.5 else [0,0,0]
            spark.extend([*rgb,255])  # Opaque black protects blur from hidden-RGB alpha bleed.
            protected = 110<x<261 and 240<y<315
            protection.extend([0,0,0,0 if protected else 255])
            amount=255 if 40<x<105 and 73<y<310 and (x*31+y*17)%107>16 else 0
            paint.extend([0,0,0,amount])
    for name, values in [('panel',panel),('lightning',spark),('protection',protection),('paint',paint)]:
        (root/f'{name}.png').write_bytes(png_bytes(size,size,4,values))
    mask={'source_artifact_id':'protection','channel':'alpha'}
    p={'schema':SCHEMA,'sources':{k:f'{k}.png' for k in ('panel','lightning','protection','paint')},
       'recipe':{'schema':'axm.raster-composition/v1','id':'AXM-salvage-storm-panel',
                 'canvas':{'width':size,'height':size},
                 'layers':[{'id':'canonical-panel','source_artifact_id':'panel'},
                           {'id':'chipped-paint','fill':'#EC9930','opacity':0.68,'blend_mode':'overlay',
                            'mask':{'source_artifact_id':'paint','channel':'alpha'}},
                           {'id':'soft-corona','source_artifact_id':'lightning','blend_mode':'screen',
                            'filters':[{'type':'blur','radius':8},{'type':'brightness','value':0.025}],
                            'opacity':0.8,'mask':mask},
                           {'id':'electrical-core','source_artifact_id':'lightning','blend_mode':'screen','mask':mask}],
                 'notes':['Original procedural demonstration; 2D texture/effect only.',
                          'The AXM nameplate remains pixel-exact; source images remain editable.']}}
    (root/'input-project.json').write_text(json.dumps(p,indent=2)+'\n')
    receipt=publish_studio_project(root/'editable',p,root)
    replay=json.loads((root/'editable/project.json').read_text())
    result=compose_studio_project(replay,root/'editable')
    assert result['png']==(root/'editable/composition.png').read_bytes()
    print(json.dumps({'output':str(root/'editable/composition.png'),'replay':'byte-identical',
                      'sha256':receipt['output_png_sha256']},indent=2))


if __name__=='__main__': build(sys.argv[1])
