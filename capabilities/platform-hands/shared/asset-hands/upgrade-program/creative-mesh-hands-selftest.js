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
assert.equal(Platform.creativeHands.audit().total,239);
assert.equal(Platform.creativeHands.recipeRegistry().count,246);

for(const kind of ['cube','sphere','cylinder','cone','plane','torus']){
  const built=Platform.creativeHands.invoke('creative.mesh-primitive.'+kind,{spec:{id:'p-'+kind,detail:12}}).result;
  assert.equal(built.schema,Mesh.SCHEMA);
  assert(built.positions.length>=9&&built.indices.length>=3);
  assert.equal(built.normals.length,built.positions.length);
  assert.equal(built.uvs.length,built.positions.length/3*2);
}

const cube=MeshHands.invoke('creative.mesh-primitive.cube',{spec:{id:'cube',detail:8}}).result;
const moved=MeshHands.invoke('creative.mesh-transform.translate',{mesh:cube,vector:[3,-2,5]}).result;
const moveBounds=Mesh.bounds(moved);assert(Math.abs(moveBounds.center[0]-3)<1e-9);assert(Math.abs(moveBounds.center[1]+2)<1e-9);assert(Math.abs(moveBounds.center[2]-5)<1e-9);
const scaled=MeshHands.invoke('creative.mesh-transform.scale',{mesh:cube,vector:[2,3,4]}).result;assert.deepEqual(Mesh.bounds(scaled).size,[4,6,8]);
const rotated=MeshHands.invoke('creative.mesh-transform.rotate-y',{mesh:cube,degrees:90}).result;assert.equal(rotated.positions.length,cube.positions.length);
for(const axis of ['x','y','z']){const mirrored=MeshHands.invoke('creative.mesh-transform.mirror-'+axis,{mesh:cube}).result;assert.equal(mirrored.indices.length,cube.indices.length);}

const inflated=MeshHands.invoke('creative.mesh-deform.inflate',{mesh:cube,amount:.1}).result;assert.notEqual(inflated.digest,cube.digest);
const twisted=MeshHands.invoke('creative.mesh-deform.twist',{mesh:cube,degrees:90}).result;assert.notEqual(twisted.digest,cube.digest);
const tapered=MeshHands.invoke('creative.mesh-deform.taper',{mesh:cube,factor:.5}).result;assert.notEqual(tapered.digest,cube.digest);
const bent=MeshHands.invoke('creative.mesh-deform.bend',{mesh:cube,degrees:45}).result;assert.notEqual(bent.digest,cube.digest);
const flattened=MeshHands.invoke('creative.mesh-deform.flatten-y',{mesh:cube,value:0}).result;assert(Mesh.bounds(flattened).size[1]<1e-12);
const noisyA=MeshHands.invoke('creative.mesh-deform.noise-displace',{mesh:cube,spec:{amount:.05,seed:'same'}}).result;
const noisyB=MeshHands.invoke('creative.mesh-deform.noise-displace',{mesh:cube,spec:{amount:.05,seed:'same'}}).result;assert.equal(noisyA.digest,noisyB.digest);

const flipped=MeshHands.invoke('creative.mesh-topology.flip-winding',{mesh:cube}).result;assert.equal(flipped.indices[1],cube.indices[2]);assert.equal(flipped.indices[2],cube.indices[1]);
const centered=MeshHands.invoke('creative.mesh-topology.center-origin',{mesh:moved}).result;assert(Mesh.bounds(centered).center.every((v)=>Math.abs(v)<1e-9));
const normalized=MeshHands.invoke('creative.mesh-topology.normalize-scale',{mesh:scaled,target:2}).result;assert(Math.abs(Math.max(...Mesh.bounds(normalized).size)-2)<1e-9);
const compacted=MeshHands.invoke('creative.mesh-topology.compact',{mesh:cube}).result;assert(compacted.positions.length<=cube.positions.length);
const welded=MeshHands.invoke('creative.mesh-topology.weld',{mesh:cube,epsilon:1e-6}).result;assert(welded.positions.length<=cube.positions.length);
const merged=MeshHands.invoke('creative.mesh-topology.merge',{meshes:[cube,Mesh.translate(cube,[4,0,0])],id:'double'}).result;assert.equal(merged.indices.length,cube.indices.length*2);
const subdivided=MeshHands.invoke('creative.mesh-topology.subdivide',{mesh:cube}).result;assert.equal(subdivided.indices.length,cube.indices.length*4);
assert.throws(()=>{let m=cube;for(let i=0;i<9;i++)m=Mesh.subdivide(m);},/budget exceeded/);

for(const id of ['planar-x','planar-y','planar-z','spherical','cylindrical','normalize']){
  const uv=MeshHands.invoke('creative.mesh-uv.'+id,{mesh:cube}).result;
  assert.equal(uv.uvs.length,uv.positions.length/3*2);
  assert(uv.uvs.every((v)=>v>=-1e-9&&v<=1+1e-9));
}
const area=MeshHands.invoke('creative.mesh-analysis.surface-area',{mesh:cube}).result;assert(area.surface_area>0);
const volume=MeshHands.invoke('creative.mesh-analysis.volume',{mesh:cube}).result;assert(volume.absolute_volume>0);
const centroid=MeshHands.invoke('creative.mesh-analysis.centroid',{mesh:cube}).result;assert(centroid.centroid.every((v)=>Math.abs(v)<1e-9));
const topology=MeshHands.invoke('creative.mesh-analysis.topology',{mesh:cube}).result;assert(topology.triangles===cube.indices.length/3);
const b=MeshHands.invoke('creative.mesh-analysis.bounds',{mesh:cube}).result;assert.deepEqual(b.size,[2,2,2]);

const recipe=Platform.creativeHands.invokeRecipe('mesh-primitive.sphere',{spec:{id:'recipe-sphere',detail:10}});assert.equal(recipe.state,'EXECUTABLE');assert.equal(recipe.result.result.schema,Mesh.SCHEMA);
console.log(JSON.stringify({status:'PASS',mesh_hands:audit.total,public_hands:Platform.creativeHands.audit().total,recipes:Platform.creativeHands.recipeRegistry().count,cube:cube.digest,subdivided:subdivided.digest,area:area.digest,volume:volume.digest},null,2));