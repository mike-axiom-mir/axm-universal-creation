"""Portable core, real 2D pixels and independently decoded animated 3D frames."""
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry,digest,instance,resolve,validate,attachment_matrix,placement_2d
from axm_stickers.placement import identity
from axm_uc import sticker_adapter as adapter
from axm_uc.fabric_noise import png_bytes
from axm_uc.procedural_3d import build_glb
from axm_uc.game_pose_runtime import GamePoseAsset,_parse
from axm_uc import studio_compositor as studio

ORIGIN={'author':'AXM test fixture','license':'CC0-1.0','source':'Original analytical fixture'}


def project(fill='#4080C0',width=2,height=2):
    return {'schema':studio.SCHEMA,'sources':{},'recipe':{
        'schema':'axm.raster-composition/v1','canvas':{'width':width,'height':height},
        'layers':[{'id':'paint','fill':fill,'opacity':1.0}]}}


def definition():
    return adapter.definition('panel','Salvage panel',adapter.STUDIO,
        {'space':'2d','socket':'surface','anchor':[0,0]}, {'project':project()}, {},
        tags=['salvage','panel'],parameters={'opacity':{
            'type':'number','min':0,'max':1,'default':1.0,
            'path':['project','recipe','layers',0,'opacity']}},**ORIGIN)


def frame(x=0,y=0,z=0,angle=0):
    s,c=math.sin(angle),math.cos(angle)
    return [c,-s,0,x,s,c,0,y,0,0,1,z,0,0,0,1]


def pixels(body):
    # Independent decoding of the PNG output scanlines.
    import struct,zlib
    at=8; data=b''
    while at<len(body):
        n=struct.unpack_from('>I',body,at)[0]; kind=body[at+4:at+8]
        if kind==b'IHDR': w,h=struct.unpack_from('>II',body,at+8)
        if kind==b'IDAT': data+=body[at+8:at+8+n]
        at+=n+12
    raw=zlib.decompress(data)
    return [tuple(raw[y*(w*4+1)+1+x*4:y*(w*4+1)+5+x*4]) for y in range(h) for x in range(w)]


class StickerFixture:

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.registry=Registry(self.root/'stickers.sqlite'); self.addCleanup(self.registry.db.close)
        self.d=definition(); self.registry.register(self.d)


class StickerCoreTests(StickerFixture, unittest.TestCase):
    def test_immutable_versions_and_pinned_independent_instances(self):
        a=instance(self.d,'left',overrides={'opacity':0.25})
        b=instance(self.d,'right')
        self.assertEqual(resolve(self.d,a)['project']['recipe']['layers'][0]['opacity'],0.25)
        self.assertEqual(resolve(self.d,b)['project']['recipe']['layers'][0]['opacity'],1.0)
        invalid=copy.deepcopy(a); invalid['sticker']['version']=True
        with self.assertRaises(ValueError): resolve(self.d,invalid)
        changed=copy.deepcopy(self.d); changed['name']='new'
        with self.assertRaisesRegex(ValueError,'immutable'): self.registry.register(changed)
        changed['version']=2; self.registry.register(changed)
        with self.assertRaisesRegex(ValueError,'pinned'): resolve(changed,a)
        self.assertEqual(self.registry.get('panel',1),self.d)
        self.assertEqual(self.registry.get('panel',2),changed)

    def test_parameters_are_declared_bounded_and_not_arbitrary_mutations(self):
        for overrides in ({'unknown':1},{'opacity':True},{'opacity':1.1},{'opacity':float('nan')},[]):
            with self.subTest(overrides=overrides),self.assertRaises(ValueError): instance(self.d,'x',overrides=overrides)
        wrong=copy.deepcopy(self.d); wrong['parameters']['opacity']['path']=['project','missing']
        with self.assertRaises(ValueError): validate(wrong)
        wrong=copy.deepcopy(self.d); wrong['parameters']['other']=copy.deepcopy(wrong['parameters']['opacity'])
        with self.assertRaisesRegex(ValueError,'overlap'): validate(wrong)
        wrong=copy.deepcopy(self.d); wrong['parameters']['opacity']['default']=0.5
        with self.assertRaisesRegex(ValueError,'canonical'): validate(wrong)

    def test_registry_index_filters_and_pagination(self):
        other=copy.deepcopy(self.d); other.update(id='other',tags=['metal'])
        self.registry.register(other)
        self.assertEqual(len(self.registry.search(tag='salvage')['entries']),1)
        self.assertEqual(len(self.registry.search(adapter=adapter.STUDIO,socket='surface')['entries']),2)
        one=self.registry.search(limit=1)
        two=self.registry.search(after=one['next_cursor'],limit=1)
        self.assertEqual(two['entries'][0]['id'],'other')
        self.assertEqual(self.registry.search(tag='absent')['entries'],[])
        with self.assertRaises(ValueError): self.registry.search(limit=1000)

    def test_bundle_preserves_exact_assets_and_provenance_across_programs(self):
        body=b'Original editable source bytes'; sha=hashlib.sha256(body).hexdigest()
        d=copy.deepcopy(self.d); d['assets']={'source':sha}; d['id']='source-fixture'
        self.registry.register(d,{sha:body})
        bundle=self.registry.bundle(d['id'],1)
        with Registry(self.root/'other.sqlite') as other:
            other.import_bundle(bundle)
            self.assertEqual(other.get(d['id'],1),d)
            self.assertEqual(other.asset(sha),body)
        bundle['assets'][sha]='Y29ycnVwdA=='
        with self.assertRaisesRegex(ValueError,'digest'): self.registry.import_bundle(bundle)
        self.assertEqual(self.registry.asset(sha),body)

    def test_missing_assets_and_bad_digest_leave_no_partial_entry(self):
        d=copy.deepcopy(self.d); d['id']='missing'; d['assets']={'one':'1'*64}
        with self.assertRaises(ValueError): self.registry.register(d)
        with self.assertRaises(ValueError): self.registry.register(d,{'1'*64:b'wrong'})
        with self.assertRaises(ValueError): self.registry.get('missing',1)
        self.assertEqual(self.registry.db.execute('SELECT count(*) FROM assets').fetchone()[0],0)

    def test_source_hash_and_wrong_database_are_checked(self):
        other=self.root/'other.sqlite'
        with sqlite3.connect(other) as db: db.execute('CREATE TABLE unrelated(x)')
        before=other.read_bytes()
        with self.assertRaises(ValueError): Registry(other)
        self.assertEqual(before,other.read_bytes())
        self.registry.db.execute('UPDATE stickers SET body=?',(json.dumps({'bad':'data'}),))
        with self.assertRaises(ValueError): self.registry.get('panel',1)

    def test_core_is_importable_without_uc_or_other_dependencies(self):
        (self.root/'isolated').mkdir()
        shutil.copytree(ROOT/'src/axm_stickers',self.root/'isolated/axm_stickers',ignore=shutil.ignore_patterns('__pycache__'))
        script="""import sys
sys.path.insert(0,sys.argv[1])
from axm_stickers import Registry
with Registry(sys.argv[2]) as r:
 assert r.search()['entries'][0]['id']=='panel'
assert not any(k.startswith('axm_uc') for k in sys.modules)
print('standalone core passed')
"""
        r=subprocess.run([sys.executable,'-I','-c',script,str(self.root/'isolated'),str(self.root/'stickers.sqlite')],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('standalone core passed',r.stdout)

    def test_3d_rotated_mount_scaling_and_socket_mismatch(self):
        d=copy.deepcopy(self.d); d['attachment']={'space':'3d','socket':'bolt','anchor':frame(1,0,0,math.pi/2)}
        p=instance(d,'x',placement={'scale':2})
        target={'space':'3d','socket':'bolt','frame':frame(4,5,6,math.pi)}
        m=attachment_matrix(d,p,target)
        actual=[sum(m[r*4+k]*[1,0,0,1][k] for k in range(4)) for r in range(3)]
        for a,b in zip(actual,[4,5,6]): self.assertAlmostEqual(a,b)
        target['socket']='eye'
        with self.assertRaisesRegex(ValueError,'socket'): attachment_matrix(d,p,target)
        target['socket']='bolt'; target['frame'][0]=3
        with self.assertRaisesRegex(ValueError,'rigid'): attachment_matrix(d,p,target)


@unittest.skipUnless(shutil.which('node'),'dedicated CI supplies Node 22')
class StickerRenderingTests(StickerFixture, unittest.TestCase):
    def test_translated_scaled_rotated_2d_pixels_and_no_source_mutation(self):
        original=copy.deepcopy(self.d)
        p=instance(self.d,'rotated',placement={'translation':[3,0],'rotation':90})
        result=adapter.stamp_layer(self.registry,[p],width=5,height=4)
        values=pixels(result['png'])
        occupied={(i%5,i//5) for i,v in enumerate(values) if v[3]}
        self.assertEqual(occupied,{(1,0),(2,0),(1,1),(2,1)})
        self.assertEqual(self.registry.get('panel',1),original)
        scaled=instance(self.d,'scaled',placement={'translation':[0,0],'scale':[2,1]})
        self.assertEqual(sum(v[3]>0 for v in pixels(adapter.stamp_layer(self.registry,[scaled],width=5,height=4)['png'])),8)

    def test_opacity_overlap_and_cache_reuse(self):
        a=instance(self.d,'a',placement={'opacity':0.5})
        b=instance(self.d,'b',placement={'opacity':0.5})
        with patch.object(adapter,'_studio_render',wraps=adapter._studio_render) as render:
            result=adapter.stamp_layer(self.registry,[a,b],width=2,height=2)
            self.assertEqual(render.call_count,1)
        self.assertEqual(result['receipt']['unique_renders'],1)
        self.assertEqual(pixels(result['png'])[0],(64,128,192,192))

    def test_duplicate_ids_bad_parameters_and_work_bounds_fail(self):
        a=instance(self.d,'a')
        with self.assertRaisesRegex(ValueError,'duplicate'): adapter.stamp_layer(self.registry,[a,a],width=2,height=2)
        with self.assertRaises(ValueError): adapter.stamp_layer(self.registry,[a],width=2,height=2,target={'space':'2d','socket':'bolt'})
        with patch.object(adapter,'MAX_WORK',1):
            with self.assertRaisesRegex(ValueError,'work budget'): adapter.stamp_layer(self.registry,[a],width=2,height=2)
        invalid=copy.deepcopy(a); invalid['placement']={'execute':'bad'}
        with self.assertRaises(ValueError): adapter.stamp_layer(self.registry,[invalid],width=2,height=2)

    def test_source_file_loss_and_scene_replay_with_editable_instances(self):
        body=png_bytes(2,2,4,bytes([20,220,120,255])*4)
        (self.root/'source.png').write_bytes(body)
        p=project(); p['sources']={'ink':'source.png'}
        p['recipe']['layers']=[{'id':'ink','source_artifact_id':'ink'}]
        d=adapter.register_studio(self.registry,p,self.root,id='ink',name='Captured ink',**ORIGIN)
        (self.root/'source.png').unlink()
        instances=[instance(d,'stamp',placement={'translation':[2,1]})]
        adapter.publish_sticker_scene(self.root/'scene',self.registry,project(width=8,height=8),self.root,instances)
        scene=json.loads((self.root/'scene/scene.json').read_text())
        with Registry(self.root/'scene/stickers.sqlite') as portable:
            adapter.publish_sticker_scene(self.root/'replay',portable,scene['host'],self.root/'scene',scene['instances'])
            self.assertEqual(portable.asset(d['assets']['ink']),body)
        self.assertEqual((self.root/'scene/preview/composition.png').read_bytes(),(self.root/'replay/preview/composition.png').read_bytes())
        with self.assertRaises(FileExistsError):
            adapter.publish_sticker_scene(self.root/'scene',self.registry,project(),self.root,instances)
        self.assertEqual(scene['instances'],instances)


class StickerGLBTests(unittest.TestCase):
    def test_animated_attachment_roundtrip_preserves_geometry_materials_and_source(self):
        source_spec={'schema':'axm.procedural-3d/v0.1','name':'Salvage socket fixture','primitives':[
            {'id':'plate','type':'box','size':[0.4,0.1,0.3],'translation':[1,0,0],
             'material':{'color':'#DFA32A','metallic':0.7,'roughness':0.6}}]}
        source=build_glb(source_spec)['body']; original_doc,original_bin=_parse(source)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'r.sqlite') as registry:
            d=adapter.register_glb(registry,source,id='plate',name='Plate',socket='bolt',anchor=frame(1,0,0),
                                   editable_source=json.dumps(source_spec).encode(),**ORIGIN)
            p=instance(d,'shoulder',placement={'scale':2})
            target={'space':'3d','socket':'bolt','frame':frame(2,3,4)}
            motion=[{'time':0,'frame':target['frame']},{'time':1,'frame':frame(4,3,4,math.pi/2)},
                    {'time':2,'frame':target['frame']}]
            result=adapter.attach_glb(registry,p,target,motion=motion)
            doc,binary=_parse(result['body'])
            self.assertEqual(doc['meshes'],original_doc['meshes'])
            self.assertEqual(doc['materials'],original_doc['materials'])
            self.assertEqual(binary[:len(original_bin)],original_bin)
            self.assertEqual(registry.asset(d['assets']['model']),source)
            asset=GamePoseAsset(result['body'])
            mount=result['receipt']['mount_node']
            for t,expected in [(0,[2,3,4]),(0.5,[3,3,4]),(1,[4,3,4]),(2,[2,3,4])]:
                pose=asset.sample('StickerSocketMotion',t,vertices=True)
                point=asset.point(pose,mount,[1,0,0])
                for a,b in zip(point,expected): self.assertAlmostEqual(a,b,places=6)
            start=asset.sample('StickerSocketMotion',0)
            end=asset.sample('StickerSocketMotion',2)
            self.assertEqual(start['world_matrices'],end['world_matrices'])
            self.assertFalse(result['receipt']['visual_approval'])
            with self.assertRaises(ValueError): adapter.attach_glb(registry,p,target,motion=motion[::-1])
            with self.assertRaises(ValueError): adapter.attach_glb(registry,p,dict(target,socket='eye'))


if __name__=='__main__': unittest.main()
