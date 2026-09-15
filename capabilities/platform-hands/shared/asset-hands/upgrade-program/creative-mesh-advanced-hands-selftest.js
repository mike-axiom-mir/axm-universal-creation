'use strict';
const assert=require('assert');
const Platform=require('../../../index');
const Advanced=require('./creative-mesh-advanced-hands');
const MeshHands=require('./creative-mesh-hands');
const EditHands=require('./creative-mesh-edit-hands');
const Mesh=require('./precision-mesh');

const audit=Advanced.audit();
assert.equal(audit.total,35);
assert.equal(audit.by_family['mesh-sculpt'],8);
assert.equal(audit.by_family['mesh-uv-edit'],11);
assert.equal(audit.by_family['mesh-topology-inspect'],9);
assert.equal(audit.by_family['mesh-modifier'],7);
assert.equal(Platform.creativeHands.audit().total,314);
assert.equal(Platform.creativeHands.recipeRegistry().count,321);

const sphere=MeshHands.invoke('creative.mesh-primitive.sphere',{spec:{id:'sculpt-sphere',detail:16}}).result;
const sculptSpec={center:[0,1,0],radius:1.2,strength:.15,falloff_power:2};
for(const id of ['grab','inflate','deflate','smooth','pinch','flatten','twist']){
  const spec=Object.assign({},sculptSpec,id==='grab'?{vector:[.2,0,0]}:{},id==='flatten'?{normal:[0,1,0]}:{},id==='twist'?{axis:[0,1,0],degrees:35}:{});
  const r=Platform.creativeHands.invoke('creative.mesh-sculpt.'+id,{mesh:sphere,spec}).result;
  assert.equal(r.mesh.schema,Mesh.SCHEMA);assert(r.changed_vertices>0);assert.notEqual(r.mesh.digest,sphere.digest);
}
const noiseA=Advanced.invoke('creative.mesh-sculpt.noise',{mesh:sphere,spec:Object.assign({},sculptSpec,{seed:'wave7'})}).result;
const noiseB=Advanced.invoke('creative.mesh-sculpt.noise',{mesh:sphere,spec:Object.assign({},sculptSpec,{seed:'wave7'})}).result;
assert.equal(noiseA.mesh.digest,noiseB.mesh.digest);

const allSphere=EditHands.invoke('creative.mesh-vertex-select.by-axis',{mesh:sphere,spec:{axis:'y',side:'positive',threshold:-2}}).result;
const uvMoved=Advanced.invoke('creative.mesh-uv-edit.translate',{mesh:sphere,selection:allSphere,spec:{u:.2,v:-.1}}).result;assert.notEqual(uvMoved.digest,sphere.digest);
const movedSelection=EditHands.invoke('creative.mesh-vertex-select.by-axis',{mesh:uvMoved,spec:{axis:'y',side:'positive',threshold:-2}}).result;
const uvNorm=Advanced.invoke('creative.mesh-uv-edit.normalize-selected',{mesh:uvMoved,selection:movedSelection}).result;assert(uvNorm.uvs.every((v)=>v>=-1e-9&&v<=1+1e-9));
for(const id of ['scale','rotate','flip-u','flip-v','wrap','clamp','planar-x','planar-y','planar-z']){
  const sel=EditHands.invoke('creative.mesh-vertex-select.by-axis',{mesh:sphere,spec:{axis:'y',side:'positive',threshold:-2}}).result;
  const args={mesh:sphere,selection:sel};if(id==='scale')args.spec={u:.8,v:1.2};if(id==='rotate')args.spec={degrees:30};
  const r=Advanced.invoke('creative.mesh-uv-edit.'+id,args).result;assert.equal(r.schema,Mesh.SCHEMA);assert.equal(r.uvs.length,sphere.uvs.length);
}

const plane=MeshHands.invoke('creative.mesh-primitive.plane',{spec:{id:'open-plane',detail:4}}).result;
const loops=Advanced.invoke('creative.mesh-topology-inspect.boundary-loops',{mesh:plane}).result;assert.equal(loops.boundary_edges,4);assert.equal(loops.components.length,1);assert.equal(loops.components[0].closed,true);
const openAudit=Advanced.invoke('creative.mesh-topology-inspect.manifold-audit',{mesh:plane}).result;assert.equal(openAudit.status,'OPEN_MANIFOLD');
const incidence=Advanced.invoke('creative.mesh-topology-inspect.edge-incidence',{mesh:plane}).result;assert.equal(incidence.boundary_edges,4);
const euler=Advanced.invoke('creative.mesh-topology-inspect.euler',{mesh:plane}).result;assert.equal(euler.euler_characteristic,1);
const faceN=Advanced.invoke('creative.mesh-topology-inspect.face-neighbors',{mesh:plane,spec:{face:0}}).result;assert.equal(faceN.neighbors.length,1);
const vertexN=Advanced.invoke('creative.mesh-topology-inspect.vertex-neighbors',{mesh:plane,spec:{vertex:0}}).result;assert(vertexN.neighbors.length>=2);
const deg=Advanced.invoke('creative.mesh-topology-inspect.degenerate-audit',{mesh:plane,spec:{epsilon:1e-10}}).result;assert.equal(deg.status,'PASS');
const orient=Advanced.invoke('creative.mesh-topology-inspect.orientation-audit',{mesh:plane}).result;assert.equal(orient.status,'PASS');
const cube=Mesh.weld(MeshHands.invoke('creative.mesh-primitive.cube',{spec:{id:'closed-cube',detail:8}}).result,1e-6);
const closedAudit=Advanced.invoke('creative.mesh-topology-inspect.manifold-audit',{mesh:cube}).result;assert.equal(closedAudit.status,'CLOSED_EDGE_MANIFOLD');
const two=Mesh.merge([cube,Mesh.translate(cube,[5,0,0])],'two-cubes');const comps=Advanced.invoke('creative.mesh-topology-inspect.connected-components',{mesh:two}).result;assert.equal(comps.count,2);

const solid=Advanced.invoke('creative.mesh-modifier.solidify',{mesh:plane,spec:{thickness:.1}}).result;assert.equal(solid.positions.length/3,8);assert.equal(solid.indices.length/3,12);
const linear=Advanced.invoke('creative.mesh-modifier.array-linear',{mesh:cube,spec:{count:3,offset:[3,0,0]}}).result;assert.equal(linear.indices.length,cube.indices.length*3);
const radial=Advanced.invoke('creative.mesh-modifier.array-radial',{mesh:cube,spec:{count:4,axis:'y',degrees:360}}).result;assert.equal(radial.indices.length,cube.indices.length*4);
const snapped=Advanced.invoke('creative.mesh-modifier.snap-grid',{mesh:sphere,spec:{step:.25}}).result;assert(snapped.positions.every((v)=>Math.abs(v/.25-Math.round(v/.25))<1e-9));
const planeSnap=Advanced.invoke('creative.mesh-modifier.snap-plane',{mesh:sphere,spec:{axis:'y',value:0,threshold:.2}}).result;assert.equal(planeSnap.schema,Mesh.SCHEMA);
const sheared=Advanced.invoke('creative.mesh-modifier.shear',{mesh:cube,spec:{target_axis:'x',source_axis:'y',factor:.25}}).result;assert.notEqual(sheared.digest,cube.digest);
const fitted=Advanced.invoke('creative.mesh-modifier.fit-bounds',{mesh:cube,spec:{min:[0,0,0],max:[2,4,6]}}).result;assert.deepEqual(Mesh.bounds(fitted).size,[2,4,6]);
assert.throws(()=>Advanced.invoke('creative.mesh-modifier.fit-bounds',{mesh:plane,spec:{min:[0,0,0],max:[1,1,1]}}),/nonzero source extent/);
const large=MeshHands.invoke('creative.mesh-primitive.sphere',{spec:{id:'large',detail:64}}).result;assert.throws(()=>Advanced.invoke('creative.mesh-modifier.array-linear',{mesh:large,spec:{count:128,offset:[1,0,0]}}),/exceed precision-mesh budget/);

const recipe=Platform.creativeHands.invokeRecipe('mesh-modifier.solidify',{mesh:plane,spec:{thickness:.05}});assert.equal(recipe.state,'EXECUTABLE');assert.equal(recipe.result.result.schema,Mesh.SCHEMA);
console.log(JSON.stringify({status:'PASS',advanced_hands:audit.total,public_hands:Platform.creativeHands.audit().total,recipes:Platform.creativeHands.recipeRegistry().count,sculpt:noiseA.mesh.digest,uv:uvNorm.digest,topology:closedAudit.digest,modifier:solid.digest},null,2));