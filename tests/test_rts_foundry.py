import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from axm_uc.rts_foundry import (catalog, articulated_glb, verify_articulated_glb,
    unpack_glb, pack_glb, read_accessor, reference_pack_request, collision_contract)
from axm_uc.rts_recipes import build_reference_mesh
from axm_uc.rts_mesh import SalvageMesh
from axm_uc.procedural_3d import build_glb, verify_glb

class RTSFoundryTests(unittest.TestCase):
 def test_all_reference_designs_export_two_real_detail_levels(self):
  data=catalog();assets=data['assets'];ids={a['id'] for a in assets}
  self.assertEqual(len(assets),83);self.assertEqual(len(ids),83)
  self.assertEqual(len(data['references']),8)
  self.assertTrue(set(data['overview_aliases'].values())<=ids)
  for asset in assets:
   counts=[]
   for lod in ('near','far'):
    with self.subTest(asset=asset['id'],lod=lod):
     f=build_reference_mesh(asset,lod);body,check=articulated_glb(f,asset['id']+'-'+lod)
     counts.append(check['triangles']);self.assertTrue(check['passed']);self.assertLess(check['triangles'],40000)
     self.assertGreater(len(body),1000)
   self.assertLess(counts[1],counts[0],asset['id'])

 def test_welded_surfaces_preserve_triangles_and_outward_volume(self):
  for operation in ('ellipsoid','roundbox','lathe','ring'):
   f=SalvageMesh()
   if operation=='ellipsoid':f.ellipsoid('test',(0,0,0),(2,2,2))
   if operation=='roundbox':f.roundbox('test',(0,0,0),(2,2,2))
   if operation=='lathe':f.lathe('test',(0,0,0),[(0,-1),(1,-1),(1,1),(0,1)])
   if operation=='ring':f.ring('test',(0,0,0),1,.2)
   spec=f.surface_spec('test');g=spec['primitives'][0]
   self.assertLess(len(g['positions']),len(f.groups['body__iron']['p']))
   volume=0
   for k in range(0,len(g['indices']),3):
    a,b,c=[g['positions'][i] for i in g['indices'][k:k+3]]
    volume+=sum(a[i]*(b[(i+1)%3]*c[(i+2)%3]-b[(i+2)%3]*c[(i+1)%3]) for i in range(3))/6
   self.assertGreater(volume,0,operation)
   verify_glb(build_glb(spec)['body'])

 def test_articulation_preserves_bind_geometry_and_real_movement(self):
  asset=next(a for a in catalog()['assets'] if a['id']=='crew-worker')
  f=build_reference_mesh(asset);before=copy.deepcopy(f.groups)
  raw,check=articulated_glb(f,'crew');self.assertEqual(f.groups,before)
  self.assertEqual(raw,articulated_glb(f,'crew')[0]);self.assertIn('walk',check['clips'])
  doc,blob=unpack_glb(raw)
  original_spec=f.surface_spec('crew')
  for node in doc['nodes']:
   p=doc['meshes'][node['mesh']]['primitives'][0];local=read_accessor(doc,blob,p['attributes']['POSITION']);original=original_spec['primitives'][node['mesh']]['positions']
   for a,b in zip(local,original):
    for j in range(3):self.assertAlmostEqual(a[j]+node['translation'][j],b[j],places=5)
  targets=[]
  for c in doc['animations'][0]['channels']:
   values=read_accessor(doc,blob,doc['animations'][0]['samplers'][c['sampler']]['output'])
   self.assertNotEqual(values[0],values[1]);targets.append(doc['nodes'][c['target']['node']]['name'])
  self.assertTrue(any(n.startswith('leg-m1') for n in targets));self.assertTrue(any(n.startswith('leg-1') for n in targets))

 def test_bad_animation_and_pivots_fail(self):
  asset=next(a for a in catalog()['assets'] if a['id']=='scrap-buggy')
  raw,_=articulated_glb(build_reference_mesh(asset),'buggy');doc,blob=unpack_glb(raw)
  bad=copy.deepcopy(doc);bad['nodes'][0]['translation'][0]=100
  with self.assertRaises(ValueError):verify_articulated_glb(pack_glb(bad,blob))
  bad=copy.deepcopy(doc);bad['animations'][0]['channels'][0]['target']['node']=999999
  with self.assertRaises(ValueError):verify_articulated_glb(pack_glb(bad,blob))
  badblob=bytearray(blob);ref=doc['animations'][0]['samplers'][0]['output'];a=doc['accessors'][ref];v=doc['bufferViews'][a['bufferView']];struct.pack_into('<f',badblob,v['byteOffset'],5)
  with self.assertRaises(ValueError):verify_articulated_glb(pack_glb(doc,badblob))

 def test_collision_keeps_gate_and_market_passages_explicit(self):
  assets={a['id']:a for a in catalog()['assets']};bounds={'min':[-3,0,-2],'max':[3,4,2]}
  gate=collision_contract(assets['spike-gate'],bounds)
  self.assertEqual([b['role'] for b in gate['boxes']],['solid','solid','gate-closed-only'])
  market=collision_contract(assets['regional-scrap-market-gate'],bounds)
  self.assertTrue(all(abs(b['center'][0])-b['size'][0]/2>1 for b in market['boxes']))
  self.assertEqual(collision_contract(assets['scrap-rifle'],bounds)['boxes'],[])

 def test_pack_uses_existing_no_overwrite_publication(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp)/'pack';request=reference_pack_request(target,['bathtub-turret']);inp=request['inputs']
   from axm_uc.machine import UniversalCreationMachine
   machine=UniversalCreationMachine(Path(__file__).resolve().parents[1])
   result=machine.create(request);self.assertEqual(result['type'],'CREATION_RESULT',result)
   raw=(target/'manifest.json').read_bytes();second=machine.create(request)
   self.assertEqual(second['type'],'CREATION_ERROR');self.assertEqual((target/'manifest.json').read_bytes(),raw)
   for entry in json.loads(raw)['items'][0]['lods']:
    self.assertEqual(hashlib.sha256((target/entry['path']).read_bytes()).hexdigest(),entry['sha256'])
  for ids in [[],['no-such-asset'],['crew-worker','crew-worker']]:
   with self.assertRaises(ValueError):reference_pack_request('unused',ids)
