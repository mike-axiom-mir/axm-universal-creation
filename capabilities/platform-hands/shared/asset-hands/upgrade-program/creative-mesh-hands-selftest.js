'use strict';
const assert=require('assert');
const MeshHands=require('./creative-mesh-hands');
const Mesh=require('./precision-mesh');
const Platform=require('../../../index');

const audit=MeshHands.audit();
assert.equal(audit.total,42);
assert.equal(audit.by_family['mesh-primitive'],6);
assert.equal(audit.by_family['mesh-transform'],8);
assert.equal(audit.by_family['mesh-deform'],8);
assert.equal(audit.by_family['mesh-topology'],9);
assert.equal(audit.by_family['mesh-uv'],6);
assert.equal(audit.by_family['mesh-analysis'],5);
assert(Platform.creativeHands.audit().total>=239);
assert(Platform.creativeHands.recipeRegistry().count>=246);

for(const kind of ['cube','sphere','cylinder','cone','plane','torus']){
  const built=Platform.creativeHands.invoke('creative.mesh-primitive.'+kind,{spec:{id:'p-'+kind,detail:12}}).result;
  assert.equal(built.schema,Mesh.SCHEMA);assert(built.positions.length>=9&&built.indices.length>=3);assert.equal(built.normals.length,built.positions.length);assert.equal(built.uvs.length,built.positions.length/3*2);
}
const cube=MeshHands.invoke('creative.mesh-primitive.cube',{spec:{id:'cube',detail:8}}).result;
const moved=MeshHands.invoke('creative.mesh-transform.translate',{mesh:cube,vector:[3,-2,5]}).result;
const moveBounds=Mesh.bounds(moved);assert(Math.abs(moveBounds.center[0]-3)<1e-9&&Math.abs(moveBounds.center[1]+2)<1e-9&&Math.abs(moveBounds.center[2]-5)<1e-9);
const scaled=MeshHands.invoke('creative.mesh-transform.scale',{mesh:cube,vector:[2,3,4]}).result;assert.deepEqual(Mesh.bounds(scaled).size,[4,6,8]);
assert.throws(()=>MeshHands.invoke('creative.mesh-transform.scale',{mesh:cube,vector:[-1,1,1]}),/use explicit mirror hands/);
for(const axis of ['x','y','z']){assert.equal(MeshHands.invoke('creative.mesh-transform.rotate-'+axis,{mesh:cube,degrees:90}).result.positions.length,cube.positions.length);assert.equal(MeshHands.invoke('creative.mesh-transform.mirror-'+axis,{mesh:cube}).result.indices.length,cube.indices.length);}

for(const [id,args] of [['inflate',{amount:.1}],['twist',{degrees:90}],['taper',{factor:.5}],['bend',{degrees:45}]])assert.notEqual(MeshHands.invoke('creative.mesh-deform.'+id,Object.assign({mesh:cube},args)).result.digest,cube.digest);
for(const axis of ['x','y','z'])assert(Mesh.bounds(MeshHands.invoke('creative.mesh-deform.flatten-'+axis,{mesh:cube,value:0}).result).size['xyz'.indexOf(axis)]<1e-12);
const noisyA=MeshHands.invoke('creative.mesh-deform.noise-displace',{mesh:cube,spec:{amount:.05,seed:'same'}}).result,noisyB=MeshHands.invoke('creative.mesh-deform.noise-displace',{mesh:cube,spec:{amount:.05,seed:'same'}}).result;assert.equal(noisyA.digest,noisyB.digest);

const flipped=MeshHands.invoke('creative.mesh-topology.flip-winding',{mesh:cube}).result;assert.equal(flipped.indices[1],cube.indices[2]);assert.equal(flipped.indices[2],cube.indices[1]);
const centered=MeshHands.invoke('creative.mesh-topology.center-origin',{mesh:moved}).result;assert(Mesh.bounds(centered).center.every((v)=>Math.abs(v)<1e-9));
const normalized=MeshHands.invoke('creative.mesh-topology.normalize-scale',{mesh:scaled,target:2}).result;assert(Math.abs(Math.max(...Mesh.bounds(normalized).size)-2)<1e-9);
const compacted=MeshHands.invoke('creative.mesh-topology.compact',{mesh:cube}).result;assert(compacted.positions.length<=cube.positions.length);
const welded=MeshHands.invoke('creative.mesh-topology.weld',{mesh:cube,epsilon:1e-6}).result;assert(welded.positions.length<=cube.positions.length);
const merged=MeshHands.invoke('creative.mesh-topology.merge',{meshes:[cube,Mesh.translate(cube,[4,0,0])],id:'double'}).result;assert.equal(merged.indices.length,cube.indices.length*2);
const subdivided=MeshHands.invoke('creative.mesh-topology.subdivide',{mesh:cube}).result;assert.equal(subdivided.indices.length,cube.indices.length*4);
const bad=Mesh.create({id:'degenerate',positions:[0,0,0,1,0,0,0,1,0,2,2,2],normals:[0,0,1,0,0,1,0,0,1,0,0,1],uvs:[0,0,1,0,0,1,1,1],indices:[0,1,2,3,3,3]});
const cleaned=MeshHands.invoke('creative.mesh-topology.remove-degenerate',{mesh:bad,epsilon:1e-10}).result;assert.equal(cleaned.indices.length,3);
const renormalized=MeshHands.invoke('creative.mesh-topology.recalc-normals',{mesh:bad}).result;assert(renormalized.normals.every(Number.isFinite));
assert.throws(()=>Mesh.primitive('sphere',{detail:65}),/outside 3\.\.64/);

for(const id of ['planar-x','planar-y','planar-z','spherical','cylindrical','normalize']){const uv=MeshHands.invoke('creative.mesh-uv.'+id,{mesh:cube}).result;assert.equal(uv.uvs.length,uv.positions.length/3*2);assert(uv.uvs.every((v)=>v>=-1e-9&&v<=1+1e-9));}
const area=MeshHands.invoke('creative.mesh-analysis.surface-area',{mesh:cube}).result;assert(area.surface_area>0);
const volume=MeshHands.invoke('creative.mesh-analysis.volume',{mesh:cube}).result;assert(volume.absolute_volume>0);
const centroid=MeshHands.invoke('creative.mesh-analysis.centroid',{mesh:cube}).result;assert(centroid.centroid.every((v)=>Math.abs(v)<1e-9));
const topology=MeshHands.invoke('creative.mesh-analysis.topology',{mesh:cube}).result;assert(topology.triangles===cube.indices.length/3);
const b=MeshHands.invoke('creative.mesh-analysis.bounds',{mesh:cube}).result;assert.deepEqual(b.size,[2,2,2]);
const recipe=Platform.creativeHands.invokeRecipe('mesh-primitive.sphere',{spec:{id:'recipe-sphere',detail:10}});assert.equal(recipe.state,'EXECUTABLE');assert.equal(recipe.result.result.schema,Mesh.SCHEMA);
console.log(JSON.stringify({status:'PASS',mesh_hands:audit.total,public_hands:Platform.creativeHands.audit().total,recipes:Platform.creativeHands.recipeRegistry().count,cube:cube.digest,subdivided:subdivided.digest,area:area.digest,volume:volume.digest},null,2));