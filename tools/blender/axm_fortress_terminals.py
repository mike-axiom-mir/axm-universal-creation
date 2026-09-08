"""Original Reactor Fortress terminals. Blender 5.x; no external assets/add-ons.

blender -b --python tools/blender/axm_fortress_terminals.py -- --output NEW_DIRECTORY
Individual named parts remain editable in .blend; exported static parts batch
only within their semantic Cabinet/Module group. All public coordinates: m, Y up.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

M = {}
SPECS = {
    'armory-relay': dict(label='RELAY', cost=120, accent=(.07,.34,.41), energy=(.13,.78,.94), kind='orb', footprint=(2,1), cap=1.65),
    'armory-foldback': dict(label='FOLDBACK', cost=140, accent=(.075,.245,.435), energy=(.10,.57,.90), kind='magazine', footprint=(2,1), cap=1.65),
    'armory-slopcaster': dict(label='SLOPCASTER', cost=130, accent=(.48,.38,.065), energy=(.57,.86,.095), kind='vessel', footprint=(2,1), cap=1.65),
    'armory-ghostline': dict(label='GHOSTLINE', cost=150, accent=(.25,.19,.44), energy=(.23,.66,.94), kind='phase', footprint=(2,1), cap=1.65),
    'utility-refill': dict(label='REFILL', cost=None, accent=(.055,.30,.28), energy=(.19,.80,.65), kind='refill', footprint=(1.4,.8), cap=1.425),
    'turret-overcharge': dict(label='OVERCHARGE', cost=100, accent=(.66,.26,.035), energy=(1,.49,.07), kind='coil', footprint=(2,1), cap=2.2),
}

def xyz(p): return (p[0], -p[2], p[1])
def pub(p): return (p[0], p[2], -p[1])
def empty(name, parent=None, p=(0,0,0)):
    o=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(o)
    o.parent=parent; o.location=xyz(p); return o
def mat(name,color,metal=0,emit=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=.38 if metal else .58
    p.inputs['Emission Color'].default_value=(*color,1); p.inputs['Emission Strength'].default_value=emit
    M[name]=m
def materials(spec):
    M.clear(); mat('Terminal_Ceramic',(.52,.60,.61)); mat('Terminal_Steel',(.13,.20,.24),.7)
    mat('Terminal_Dark',(.025,.039,.045),.35); mat('Terminal_Rubber',(.016,.022,.026))
    mat('Terminal_Accent',spec['accent'],.35); mat('Terminal_Power',spec['energy'],.2,1.3)
def finish(o,name,material,parent,bevel=0):
    o.name=name; o.data.materials.append(M['Terminal_'+material]); o.parent=parent
    if bevel:
        # Half-thickness clamping collapses opposing bevel faces on thin pulls,
        # panels and windows. Keep a real central face in the editable source.
        m=o.modifiers.new('Machined edge','BEVEL'); m.width=min(bevel,min(o.dimensions)*.45); m.segments=1
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=m.name)
    return o
def box(name,p,size,material,parent,bevel=.012):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(p)); o=bpy.context.object
    o.scale=(size[0],size[2],size[1]); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,material,parent,bevel)
def cyl(name,p,r,depth,material,parent,axis='Y',n=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=depth,location=xyz(p)); o=bpy.context.object
    if axis=='X': o.rotation_euler.y=math.pi/2
    if axis=='Z': o.rotation_euler.x=math.pi/2
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=False)
    for f in o.data.polygons: f.use_smooth=len(f.vertices)==4
    return finish(o,name,material,parent,.004)
def ring(name,p,outer,inner,depth,material,parent,axis='Y',n=24):
    vs=[]
    for h in (-depth/2,depth/2):
        for r in (outer,inner):
            for i in range(n):
                a=i*math.tau/n; q=(r*math.cos(a),h,r*math.sin(a))
                if axis=='Z': q=(q[0],q[2],q[1])
                vs.append(xyz(tuple(q[k]+p[k] for k in range(3))))
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces += [(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)]
    return mesh(name,vs,faces,material,parent)
def mesh(name,vs,faces,material,parent):
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],faces); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); return finish(o,name,material,parent)
def orb(name,p,r,material,parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=r,location=xyz(p))
    o=finish(bpy.context.object,name,material,parent)
    for f in o.data.polygons:f.use_smooth=True
    return o
def textmesh(name,body,p,size,parent,back=False):
    cu=bpy.data.curves.new(name,'FONT'); cu.body=body; cu.align_x='CENTER'; cu.size=size
    cu.extrude=0; cu.resolution_u=1
    o=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(o); o.location=xyz(p)
    o.rotation_euler=(math.pi/2,0,math.pi if back else 0)
    bpy.context.view_layer.objects.active=o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o=bpy.context.object; o.select_set(False)
    return finish(o,name,'Ceramic',parent)
def bolts(parent,width,z,y):
    for x in (-width/2,width/2): cyl('Captive_hex_fastener',(x,y,z),.019,.012,'Steel',parent,'Z',6)
def face(parent,w,d,label,cost,short=False):
    # Mirrored rear face keeps function discoverable without rotating the footprint.
    for sign in (-1,1):
        z=sign*(d/2-.033)
        box('Inset_face_gasket',(0,.86,z),(w-.31,.44,.026),'Rubber',parent,.018)
        box('Inset_display',(0,.89,z+sign*.016),(w-.42,.27,.016),'Dark',parent,.007)
        textmesh('Function_engraving',label,(0,.895,z+sign*.027),.083 if not short else .073,parent,sign<0)
        if cost is not None:textmesh('Price_plate',str(cost)+' CR',(0,.795,z+sign*.027),.058,parent,sign<0)
        else:textmesh('Selected_utility_plate','SELECTED / 2 MAX',(0,.795,z+sign*.027),.040,parent,sign<0)
        for x in (-1,1):box('Status_bar',(x*(w/2-.17),.88,z+sign*.017),(.035,.22,.019),'Power',parent,.003)
        # Real access-panel gap, visible pull, paired captive bolts; within casing.
        box('Lower_service_panel',(0,.41,z),(w-.45,.40,.025),'Steel',parent,.016)
        box('Recessed_pull',(0,.49,z+sign*.015),(.23,.04,.013),'Dark',parent,.008)
        bolts(parent,w-.65,z+sign*.019,.27)
def cabinet(root,w=2,d=1,utility=False):
    g=empty('Cabinet',root)
    box('Anchored_plinth',(0,.05,0),(w,.10,d),'Steel',g,.025)
    box('Isolation_seal',(0,.118,0),(w-.08,.036,d-.05),'Rubber',g,.008)
    box('Cabinet_chassis',(0,.65,0),(w-.16,1.03,d-.10),'Dark',g,.030)
    # Corner posts and flush side armour reinforce the low horizontal silhouette.
    for sign in (-1,1):
        box('Side_armour',(sign*(w/2-.085),.64,0),(.10,.96,d-.15),'Ceramic',g,.025)
        box('Service_side_inset',(sign*(w/2-.028),.62,0),(.012,.48,d-.35),'Steel',g,.004)
        for z in (-.17,0,.17):box('Side_cooling_recess',(sign*(w/2-.020),.62,z),(.008,.25,.026),'Dark',g,.002)
        for z in (-(d/2-.11),d/2-.11):box('Corner_shoe',(sign*(w/2-.095),.19,z),(.13,.15,.12),'Steel',g,.010)
    top=1.17 if utility else 1.23
    box('Worktop_gasket',(0,top-.056,0),(w-.12,.04,d-.05),'Rubber',g,.010)
    box('Chamfered_worktop',(0,top,0),(w-.06,.075,d-.04),'Ceramic',g,.020)
    return g
def armory(root,spec):
    base=cabinet(root)
    # Shared cabinet geometry, including unpriced empty screen recesses.
    face(base,2,1,'ARMORY',None)
    # Remove utility-only line; armory base's shared service legend has no mechanic.
    for o in list(base.children):
        if o.name.startswith('Selected_utility_plate'):bpy.data.objects.remove(o,do_unlink=True)
    mod=empty('WeaponModule',root)
    box('Module_mount',(0,1.298,0),(1.25,.06,.55),'Steel',mod,.016)
    for sign in (-1,1):
        box('Identity_fascia',(0,1.295,sign*.272),(1.25,.07,.038),'Accent',mod,.006)
        textmesh('Weapon_identity',spec['label']+' / '+str(spec['cost']),(0,1.275,sign*.294),.058,mod,sign<0)
    kind=spec['kind']
    if kind=='orb':
        orb('Relay_orb',(0,1.475,0),.135,'Power',mod)
        for x in (-.28,.28):
            box('Orb_cradle_upright',(x,1.465,0),(.105,.30,.29),'Accent',mod,.02)
            cyl('Orb_pole',(x*.62,1.475,0),.073,.068,'Steel',mod,'X')
        ring('Orb_equator',(0,1.475,0),.164,.147,.023,'Steel',mod)
        for x in (-.48,.48):box('Relay_capacitor',(x,1.405,0),(.14,.15,.31),'Dark',mod,.020)
    elif kind=='magazine':
        for x in (-.29,0,.29):
            box('Magazine_dock',(x,1.347,0),(.22,.09,.36),'Rubber',mod,.015)
            box('Stored_foldback_magazine',(x,1.485,0),(.165,.29,.26),'Accent',mod,.022)
            box('Magazine_cell',(x,1.50,.137),(.10,.16,.016),'Power',mod,.004)
            for y in (1.41,1.47,1.53):box('Magazine_grip_rib',(x,y,-.139),(.12,.014,.019),'Steel',mod,.003)
        for x in (-.51,.51):box('Rack_latch',(x,1.40,0),(.13,.14,.32),'Ceramic',mod,.015)
    elif kind=='vessel':
        cyl('Slop_pressure_vessel',(0,1.475,0),.22,.28,'Accent',mod,'Y',20)
        cyl('Pressure_lid',(0,1.625,0),.23,.025,'Steel',mod,'Y',20)
        ring('Vessel_base_seat',(0,1.343,0),.255,.18,.03,'Steel',mod)
        for x in (-.46,.46):
            cyl('Compression_piston',(x,1.43,0),.065,.19,'Ceramic',mod)
            box('Piston_feed',(x*.6,1.375,0),(.27,.035,.055),'Steel',mod,.007)
        for sign in (-1,1):box('Fluid_level_window',(0,1.486,sign*.214),(.092,.16,.028),'Power',mod,.014)
        cyl('Pressure_gauge',(.39,1.535,.10),.065,.06,'Dark',mod,'Z')
        box('Gauge_needle',(.39,1.55,.133),(.014,.045,.006),'Power',mod,.002)
    elif kind=='phase':
        for x in (-.28,.28):
            box('Phase_rail',(x,1.47,0),(.17,.285,.24),'Accent',mod,.028)
            box('Phase_edge',(x*.70,1.475,0),(.029,.24,.16),'Power',mod,.006)
        box('Phase_return_bridge',(0,1.337,0),(.54,.027,.25),'Steel',mod,.006)
        for x in (-.51,.51):
            box('Phase_heat_sink',(x,1.43,0),(.13,.18,.32),'Steel',mod,.008)
            for z in (-.10,0,.10):box('Heat_sink_groove',(x,1.515,z),(.10,.016,.022),'Dark',mod,.002)
    return base,mod
def refill(root,spec):
    base=cabinet(root,1.4,.8,True);face(base,1.4,.8,'REFILL',None,True)
    mod=empty('RefillModule',root)
    box('Four_cell_docking_plate',(0,1.230,0),(1.12,.045,.53),'Steel',mod,.018)
    for i,x in enumerate((-.405,-.135,.135,.405)):
        cyl('Universal_refill_cell_'+str(i+1),(x,1.317,0),.096,.13,'Accent',mod)
        cyl('Dock_status_cap_'+str(i+1),(x,1.391,0),.084,.02,'Power',mod)
        for s in (-1,1):box('Cell_retaining_jaw',(x,1.30,s*.115),(.16,.11,.035),'Ceramic',mod,.009)
    # Inward-facing side service cue works at both east/west fixed locations.
    for sign in (-1,1):
        box('Side_refill_status',(sign*.694,.91,0),(.008,.045,.30),'Power',mod,.002)
        box('Side_refill_plus_vertical',(sign*.694,.80,0),(.008,.12,.031),'Ceramic',mod,.002)
        box('Side_refill_plus_horizontal',(sign*.694,.80,0),(.008,.031,.12),'Ceramic',mod,.002)
    return base,mod
def overcharge(root,spec):
    base=cabinet(root);face(base,2,1,'OVERCHARGE',100)
    mod=empty('OverchargeModule',root)
    cyl('Coil_isolation_seat',(0,1.32,0),.32,.11,'Rubber',mod,'Y',24)
    cyl('Power_core',(0,1.60,0),.165,.48,'Power',mod,'Y',24)
    for y in (1.39,1.52,1.65,1.78):ring('Induction_ring',(0,y,0),.26,.19,.05,'Accent',mod,n=24)
    for a in (0,math.pi/2,math.pi,math.pi*1.5):
        x,z=.31*math.cos(a),.31*math.sin(a)
        box('Protective_coil_stay',(x,1.605,z),(.055,.55,.055),'Steel',mod,.008)
    cyl('Coil_crown',(0,1.903,0),.35,.08,'Ceramic',mod,'Y',24)
    cyl('Power_status_cap',(0,1.957,0),.15,.027,'Power',mod,'Y',20)
    for x in (-.68,.68):
        box('Capacitor_bank',(x,1.40,0),(.33,.23,.57),'Accent',mod,.023)
        for z in (-.19,0,.19):box('Capacitor_cooling_fin',(x,1.522,z),(.24,.025,.045),'Steel',mod,.004)
        box('Power_bus',(x*.59,1.32,0),(.31,.04,.10),'Steel',mod,.007)
    return base,mod
def objects(group):return [o for o in group.children_recursive if o.type=='MESH']
def bounds(obs):
    pts=[pub(o.matrix_world@v.co) for o in obs for v in o.data.vertices]
    return [[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]
def bbox(b):
    return dict(x=(b[0][0]+b[0][1])/2,z=(b[2][0]+b[2][1])/2,w=b[0][1]-b[0][0],d=b[2][1]-b[2][0],bottom=b[1][0],h=b[1][1])
def geometry_digest(obs):
    rows=[]
    for o in sorted(obs,key=lambda o:o.name):
        rows.append([o.name,[[round(float(q),7) for q in pub(o.matrix_world@v.co)] for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons],o.data.materials[0].name])
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
def batch(group):
    bymat={}
    for o in objects(group):bymat.setdefault(o.data.materials[0].name,[]).append(o)
    for material,obs in bymat.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:o.select_set(True)
        bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();o=bpy.context.object
        o.name=group.name+'__'+material;o.parent=group
def setup_render():
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('StudioWorld');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.065,.085,.10,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
    scene.view_settings.view_transform='AgX'
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='PreviewCamera';scene.camera=cam
    for name,p,power,size in [('Key',(3,5,4),1000,4),('Fill',(-4,3,1),750,3),('Rim',(1,4,-3),1200,3)]:
        bpy.ops.object.light_add(type='AREA',location=xyz(p));o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size
        o.rotation_euler=(Vector(xyz((0,.8,0)))-o.location).to_track_quat('-Z','Y').to_euler()
    return scene,cam
def render(root,path,view='hero',res=(900,720)):
    scene=bpy.context.scene;cam=scene.camera;scene.render.resolution_x,scene.render.resolution_y=res
    if view in ('hero','rear'):
        cam.data.type='ORTHO';cam.location=xyz((3.6,2.8,4.8 if view=='hero' else -4.8))
        bb=bounds(objects(root));center=Vector(xyz(tuple((lo+hi)/2 for lo,hi in bb)))
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();q=cam.rotation_euler.to_quaternion()
        pts=[q.inverted()@(o.matrix_world@v.co) for o in objects(root) for v in o.data.vertices]
        lo=[min(p[k] for p in pts) for k in (0,1)];hi=[max(p[k] for p in pts) for k in (0,1)]
        eye=q.inverted()@cam.location;cam.location+=q@Vector(((lo[0]+hi[0])/2-eye.x,(lo[1]+hi[1])/2-eye.y,0))
        cam.data.ortho_scale=max(hi[0]-lo[0],(hi[1]-lo[1])*res[0]/res[1])*1.18
    else:
        # Match game world camera's default vertical FOV82; chest-height target.
        dist=2.5 if view=='near' else 6.0;cam.data.type='PERSP';cam.data.sensor_fit='VERTICAL'
        cam.data.sensor_height=32;cam.data.lens=16/math.tan(math.radians(82)/2)
        cam.location=xyz((0,1.65,dist));cam.rotation_euler=(Vector(xyz((0,.95,0)))-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update();scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
def check(root,groups,spec):
    b=bounds(objects(root));w,d=spec['footprint'];eps=2e-5
    assert b[0][0]>=-w/2-eps and b[0][1]<=w/2+eps and b[2][0]>=-d/2-eps and b[2][1]<=d/2+eps,b
    assert abs(b[1][0])<eps and b[1][1]<=spec['cap']+eps,b
    rows=[];tri=0;prims=0
    for g in groups:
        bs=bounds(objects(g));boxc=bbox(bs);n=0
        for o in objects(g):o.data.calc_loop_triangles();n+=len(o.data.loop_triangles)
        rows.append(dict(group=g.name,bounds_xyz_m=bs,box=boxc,triangles=n));tri+=n;prims+=len(objects(g))
    assert tri<8000,(root.name,tri)
    return dict(bounds_xyz_m=b,dimensions_xyz_m=[hi-lo for lo,hi in b],triangles=tri,mesh_objects=prims,collision=rows)
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--only',choices=SPECS);p.add_argument('--no-render',action='store_true');p.add_argument('--replace-unsealed-asset',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);reports=[]
    if args.replace_unsealed_asset:assert args.only and not (out.parent/'READY.json').exists(),'Replace only one explicitly selected, unsealed asset'
    for name,spec in SPECS.items():
        if args.only and name!=args.only:continue
        target=out/name;target.mkdir(exist_ok=args.replace_unsealed_asset);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;materials(spec)
        root=empty(''.join(x.title() for x in name.split('-'))+'Root')
        groups=armory(root,spec) if name.startswith('armory') else refill(root,spec) if spec['kind']=='refill' else overcharge(root,spec)
        empty('Contact',root);empty('InteractOrigin',root);empty('ServiceFront',root,(0,1.0,spec['footprint'][1]/2));empty('ServiceRear',root,(0,1,-spec['footprint'][1]/2))
        empty('StatusOrigin',root,(0,1.2 if spec['kind']=='refill' else 1.3,.43 if spec['kind']!='refill' else .33))
        bpy.context.view_layer.update();source=check(root,groups,spec);cabinet_sha=geometry_digest(objects(groups[0]));root_name=root.name;group_names=[g.name for g in groups]
        # Save exactly the editable asset: no cameras, lights or preview geometry.
        bpy.ops.wm.save_as_mainfile(filepath=str(target/(name+'.blend')))
        if not args.no_render:setup_render();render(root,target/'source-hero.png')
        # Export selected root, meshes and marker empties only.
        for g in groups:batch(g)
        bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
        for o in root.children_recursive:o.select_set(True)
        glb=target/(name+'.glb');bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,export_animations=False)
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(glb))
        root=bpy.data.objects[root_name];groups=[bpy.data.objects[n] for n in group_names];bpy.context.view_layer.update();imported=check(root,groups,spec)
        delta=max(abs(source['bounds_xyz_m'][i][j]-imported['bounds_xyz_m'][i][j]) for i in range(3) for j in range(2));assert delta<2e-5
        assert imported['mesh_objects']<=12
        assert root.location.length<1e-6 and all(abs(v-1)<1e-6 for v in root.scale) and root.rotation_euler.to_quaternion().angle<1e-6
        markers={o.name:list(pub(o.matrix_world.translation)) for o in root.children_recursive if o.type=='EMPTY' and o.name not in group_names}
        report=dict(asset=name,root=root_name,spec=spec,sha256=hashlib.sha256(glb.read_bytes()).hexdigest(),source=source,imported=imported,source_to_import_max_bounds_delta_m=delta,cabinet_geometry_sha256=cabinet_sha,markers=markers,materials=[m.name for m in bpy.data.materials],animations=[],status='PASS')
        (target/'manifest.json').write_text(json.dumps(report,indent=2));reports.append(report)
        if not args.no_render:
            setup_render();render(root,target/'import-hero.png');render(root,target/'import-rear.png','rear')
            render(root,target/'import-solo-2.5m.png','near',(1280,720));render(root,target/'import-four-view-6m.png','far',(640,360))
        print(json.dumps(dict(asset=name,triangles=imported['triangles'],primitives=imported['mesh_objects'],status='ASSET_PASS')),flush=True)
    reports=[json.loads((out/n/'manifest.json').read_text()) for n in SPECS if (out/n/'manifest.json').exists()]
    (out/'manifest.json').write_text(json.dumps(dict(units='metres',up='+Y',front='+Z',assets=reports,scope='Static source/fresh-import geometry, local component AABBs and offline studio/apparent-size renders. No gameplay or controller certification.'),indent=2))
    print('ALL_REQUESTED_ASSETS_PASS',flush=True)
if __name__=='__main__':main()
