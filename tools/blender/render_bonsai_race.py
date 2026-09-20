from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from PIL import Image, ImageDraw


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()


def add_area(name, loc, energy, size, color):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy
    data.shape='DISK'
    data.size=size
    data.color=color
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location=loc
    look_at(obj,(0,0,0.9))
    return obj


def render_view(root:Path, name:str, azimuth:float, resolution:int):
    scene=bpy.context.scene
    cam=scene.camera
    radius=4.1
    cam.location=(math.sin(azimuth)*radius,-math.cos(azimuth)*radius,1.20)
    look_at(cam,(0,0,0.95))
    scene.render.filepath=str(root/f'{name}.png')
    scene.render.resolution_x=resolution
    scene.render.resolution_y=resolution
    scene.render.resolution_percentage=100
    bpy.ops.render.render(write_still=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--directory',required=True)
    ap.add_argument('--resolution',type=int,default=720)
    args=ap.parse_args()
    root=Path(args.directory)
    glb=root/'bonsai-race-v0.1.glb'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))

    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world.color=(0.025,0.028,0.022)

    bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-0.015))
    ground=bpy.context.object
    ground.name='proof_ground'
    gm=bpy.data.materials.new('ProofGround')
    gm.diffuse_color=(0.055,0.06,0.045,1)
    ground.data.materials.append(gm)

    cam_data=bpy.data.cameras.new('proof_camera')
    cam=bpy.data.objects.new('proof_camera',cam_data)
    bpy.context.collection.objects.link(cam)
    cam.data.lens=58
    scene.camera=cam

    add_area('key',(-2.5,-3.5,4.0),1000,4.0,(1.0,0.72,0.50))
    add_area('fill',(3.2,-1.5,2.5),700,3.0,(0.45,0.65,1.0))
    add_area('rim',(1.5,3.5,3.6),900,3.0,(0.65,0.90,0.55))
    add_area('top',(-0.5,0.0,5.0),650,2.5,(1.0,0.92,0.72))

    views=[('front',0.0),('threequarter',math.radians(35)),('side',math.radians(90)),('back',math.radians(180))]
    for name,az in views:
        render_view(root,name,az,args.resolution)

    imgs=[Image.open(root/f'{name}.png').convert('RGB') for name,_ in views]
    w,h=imgs[0].size
    sheet=Image.new('RGB',(w*2,h*2),(18,20,16))
    for idx,img in enumerate(imgs):
        sheet.paste(img,((idx%2)*w,(idx//2)*h))
    draw=ImageDraw.Draw(sheet)
    labels=['FRONT','THREE-QUARTER','SIDE','BACK']
    for idx,label in enumerate(labels):
        draw.rectangle(((idx%2)*w+16,(idx//2)*h+16,(idx%2)*w+210,(idx//2)*h+52),fill=(18,20,16))
        draw.text(((idx%2)*w+28,(idx//2)*h+25),label,fill=(235,225,196))
    sheet.save(root/'turnaround-proof.png')

    report={
        'schema':'axm.uc.bonsai-race-render-proof/v0.1',
        'source':'fresh import of bonsai-race-v0.1.glb',
        'renderer':'BLENDER_EEVEE_NEXT',
        'resolution':args.resolution,
        'views':[name+'.png' for name,_ in views],
        'contact_sheet':'turnaround-proof.png',
        'boundary':'render existence is evidence of fresh-import renderability, not automatic visual acceptance',
    }
    (root/'render-proof.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
