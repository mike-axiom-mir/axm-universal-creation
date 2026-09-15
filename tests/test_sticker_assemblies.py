"""Saved recursive parts, atomic portability and decoded animated geometry."""
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_stickers import Registry,instance
from axm_stickers.assembly import save_assembly,expand,library_bundle,import_library,ASSEMBLY
from axm_stickers.placement import identity
from axm_uc.sticker_create import execute
from axm_uc.sticker_adapter import attach_glb,register_glb
from axm_uc.sticker_assembly import export_assembly
from axm_uc.game_pose_runtime import GamePoseAsset,_parse

ORIGIN={'author':'AXM','license':'CC0-1.0','source':'Original assembly analytical fixture'}

def frame(x=0,y=0):
    m=identity();m[3]=x;m[7]=y;return m

def child(d,id,x=0,*,motion=None,clip=None):
    return {'instance':instance(d,id),'target':{'space':'3d','socket':'mount','frame':frame(x)},'motion':motion,'clip':clip}

def create(registry,id='bolt',color='#B07825'):
    return execute(registry,{'operation':'create_3d','id':id,'name':'Reusable bolt','socket':'mount',**ORIGIN,
        'spec':{'schema':'axm.procedural-3d/v0.1','name':'Original bolt',
                'primitives':[{'id':'body','type':'box','size':[.2,.2,.2],'translation':[0,0,0],
                               'material':{'color':color,'metallic':.5,'roughness':.6}}]}},'.')

class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.r=Registry(self.root/'r.sqlite');self.addCleanup(self.r.db.close)
        self.d=create(self.r)
    def group(self,id,children):
        return save_assembly(self.r,id=id,name=id,children=children,origin=ORIGIN)

    def test_nested_group_is_editable_and_instances_have_independent_motion(self):
        group=self.group('pair',[child(self.d,'a'),child(self.d,'b',1)])
        trace=[{'time':0,'frame':frame(3)},{'time':1,'frame':frame(4)},{'time':2,'frame':frame(3)}]
        root=self.group('machine',[child(group,'fixed',0),child(group,'moving',3,motion=trace)])
        before=library_bundle(self.r,'machine',1)
        result=export_assembly(self.r,'machine',1); asset=GamePoseAsset(result['body'])
        for t,x in [(0,4),(.5,4.5),(1,5),(2,4)]:
            pose=asset.sample('AssemblyMotion',t,vertices=True)
            at=result['receipt']['mappings']['root/moving/b']['mount']
            self.assertAlmostEqual(asset.point(pose,at)[0],x)
            at=result['receipt']['mappings']['root/fixed/b']['mount']
            self.assertAlmostEqual(asset.point(pose,at)[0],1)
        self.assertEqual(library_bundle(self.r,'machine',1),before)
        self.assertEqual(result['receipt']['unique_source_glbs'],1)
        self.assertEqual(result['receipt']['mesh_resources'],1)
        self.assertEqual(asset.sample('AssemblyMotion',0)['world_matrices'],asset.sample('AssemblyMotion',2)['world_matrices'])

    def test_library_closure_reimports_without_original_database(self):
        g=self.group('cluster',[child(self.d,'bolt')]); self.group('asset',[child(g,'left'),child(g,'right',3)])
        bundle=library_bundle(self.r,'asset',1)
        self.assertEqual(len(bundle['definitions']),3)
        with Registry(self.root/'portable.sqlite') as other:
            import_library(other,bundle)
            self.assertEqual(export_assembly(other,'asset',1)['body'],export_assembly(self.r,'asset',1)['body'])
            self.assertEqual(other.asset(self.d['assets']['editable-source']),self.r.asset(self.d['assets']['editable-source']))

    def test_bad_library_is_atomic_and_cannot_smuggle_unrelated_definitions(self):
        self.group('group',[child(self.d,'bolt')]);bundle=library_bundle(self.r,'group',1)
        with Registry(self.root/'portable.sqlite') as other:
            bad=copy.deepcopy(bundle);bad['assets'][next(iter(bad['assets']))]='YmFk'
            with self.assertRaises(ValueError): import_library(other,bad)
            self.assertEqual(other.search()['entries'],[])
            self.assertEqual(other.db.execute('SELECT count(*) FROM assets').fetchone()[0],0)
            bad=copy.deepcopy(bundle);bad['definitions']=bad['definitions'][:1]
            with self.assertRaises(ValueError): import_library(other,bad)
            bad=copy.deepcopy(bundle);extra=copy.deepcopy(self.d);extra['id']='unrelated';bad['definitions'].append(extra)
            with self.assertRaises(ValueError): import_library(other,bad)

    def test_invalid_groups_not_saved_and_expansion_is_bounded(self):
        c=child(self.d,'same')
        with self.assertRaises(ValueError): self.group('duplicate',[c,c])
        c=child(self.d,'wrong');c['target']['socket']='incompatible'
        with self.assertRaises(ValueError): self.group('wrong',[c])
        c=child(self.d,'pin');c['instance']['sticker']['digest']='0'*64
        with self.assertRaises(ValueError): self.group('pin',[c])
        group=self.d
        for i in range(15): group=self.group('depth'+str(i),[child(group,'nested')])
        with self.assertRaisesRegex(ValueError,'budget'): self.group('too-deep',[child(group,'nested')])
        with self.assertRaises(ValueError): self.r.get('too-deep',1)

    def test_many_geometry_instances_share_resources(self):
        self.group('hundreds',[child(self.d,'bolt'+str(i),i*.3) for i in range(300)])
        result=export_assembly(self.r,'hundreds',1);doc,_=_parse(result['body'])
        self.assertEqual(len(doc['meshes']),1)
        self.assertEqual(sum('mesh' in n for n in doc['nodes']),300)
        self.assertLess(result['receipt']['nodes'],1000)
        GamePoseAsset(result['body'])

    def test_selected_source_animation_retained_in_assembly_clip(self):
        trace=[{'time':0,'frame':frame()},{'time':1,'frame':frame(2)}]
        animated=attach_glb(self.r,instance(self.d,'moving'),{'space':'3d','socket':'mount','frame':frame()},motion=trace,clip='Slide')['body']
        d=register_glb(self.r,animated,id='slider',name='Slider',socket='mount',**ORIGIN)
        self.group('machine',[child(d,'arm',3,clip='Slide')])
        result=export_assembly(self.r,'machine',1);asset=GamePoseAsset(result['body']);doc,_=_parse(result['body'])
        n=next(i for i,n in enumerate(doc['nodes']) if n.get('name')=='root/arm/moving.socket')
        self.assertAlmostEqual(asset.point(asset.sample('AssemblyMotion',.5),n)[0],4)
        self.assertIn('root/arm::Slide',[a['name'] for a in doc['animations']])
        bad=self.group('missing-clip',[child(d,'arm',clip='missing')])
        with self.assertRaisesRegex(ValueError,'unknown source clip'): export_assembly(self.r,bad['id'],1)

    def test_two_source_resource_offsets_preserve_material_and_vertices(self):
        other=create(self.r,'blue','#2040F0');self.group('mixed',[child(self.d,'a'),child(other,'b',3)])
        result=export_assembly(self.r,'mixed',1);doc,_=_parse(result['body'])
        self.assertEqual(len(doc['meshes']),2)
        self.assertNotEqual(doc['meshes'][0]['primitives'][0]['material'],doc['meshes'][1]['primitives'][0]['material'])
        pose=GamePoseAsset(result['body']).sample(None,0,vertices=True)
        centers=[sum(p[0] for p in m['positions'])/len(m['positions']) for m in pose['meshes']]
        self.assertAlmostEqual(centers[1]-centers[0],3)

    def test_embedded_texture_channels_remap_to_second_source_exactly(self):
        import struct
        from axm_uc.fabric_noise import png_bytes
        doc,raw=_parse(self.r.asset(self.d['assets']['model']))
        image=png_bytes(1,1,4,bytes([15,190,120,255]));start=len(raw)
        raw+=image
        view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(image)})
        doc['images']=[{'bufferView':view,'mimeType':'image/png'}];doc['textures']=[{'source':0,'sampler':0}];doc['samplers']=[{}]
        mat=doc['materials'][0];mat['pbrMetallicRoughness']['baseColorTexture']={'index':0}
        mat['pbrMetallicRoughness']['metallicRoughnessTexture']={'index':0}
        for key in ('normalTexture','occlusionTexture','emissiveTexture'): mat[key]={'index':0}
        doc['buffers'][0]['byteLength']=len(raw)
        js=json.dumps(doc).encode();js+=b' '*(-len(js)%4);raw+=b'\0'*(-len(raw)%4)
        body=struct.pack('<4sII',b'glTF',2,28+len(js)+len(raw))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(raw),0x004E4942)+raw
        textured=register_glb(self.r,body,id='textured',name='Textured',socket='mount',**ORIGIN)
        self.group('textures',[child(self.d,'plain'),child(textured,'paint',3)])
        result=export_assembly(self.r,'textures',1);out,binary=_parse(result['body'])
        m=out['materials'][out['meshes'][1]['primitives'][0]['material']]
        for container,key in [(m,k) for k in ('normalTexture','occlusionTexture','emissiveTexture')]+[(m['pbrMetallicRoughness'],k) for k in ('baseColorTexture','metallicRoughnessTexture')]:
            tex=out['textures'][container[key]['index']];im=out['images'][tex['source']];v=out['bufferViews'][im['bufferView']]
            self.assertEqual(binary[v['byteOffset']:v['byteOffset']+v['byteLength']],image)

    def test_human_and_machine_cli_save_and_reload_the_same_requests(self):
        request={'operation':'save_assembly','id':'saved','name':'Saved group','children':[child(self.d,'part')],'origin':ORIGIN}
        path=self.root/'request.json';path.write_text(json.dumps(request))
        run=subprocess.run([sys.executable,'-m','axm_stickers',str(self.root/'r.sqlite'),str(path)],cwd=self.root,
            env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src')},capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout),self.r.get('saved',1))
        execute(self.r,{'operation':'export_assembly','id':'saved','ver':1,'output':'asset.glb'},self.root)
        GamePoseAsset((self.root/'asset.glb').read_bytes())
        with self.assertRaises(FileExistsError): execute(self.r,{'operation':'export_assembly','id':'saved','ver':1,'output':'asset.glb'},self.root)

    def test_batch_collision_rolls_back_all_prior_items(self):
        a=copy.deepcopy(self.d);a['id']='new';bad=copy.deepcopy(self.d);bad['name']='conflict'
        with self.assertRaises(ValueError): self.r.register_many([a,bad])
        with self.assertRaises(ValueError): self.r.get('new',1)
        self.assertEqual(self.r.get(self.d['id'],1),self.d)

if __name__=='__main__': unittest.main()
