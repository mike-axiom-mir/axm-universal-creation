'use strict';
const assert=require('assert');
const Platform=require('../../../index');
const MeshHands=require('./creative-mesh-hands');
const EditHands=require('./creative-mesh-edit-hands');
const Mesh=require('./precision-mesh');

function gridMesh(detail){const positions=[],uvs=[],indices=[];for(let z=0;z<=detail;z++)for(let x=0;x<=detail;x++){positions.push(-1+2*x/detail,0,-1+2*z/detail);uvs.push(x/detail,z/detail);}for(let z=0;z<detail;z++)for(let x=0;x<detail;x++){const a=z*(detail+1)+x,b=a+1,d=(z+1)*(detail+1)+x,c=d+1;indices.push(a,c,b,a,d,c);}return Mesh.create({id:'grid',positions,indices,uvs});}

const audit=EditHands.audit();
assert.equal(audit.total,40);
assert.equal(audit.by_family['mesh-face-select'],7);
assert.equal(audit.by_family['mesh-vertex-select'],5);
assert.equal(audit.by_family['mesh-selection'],7);
assert.equal(audit.by_family['mesh-face-edit'],7);
assert.equal(audit.by_family['mesh-vertex-edit'],7);
assert.equal(audit.by_family['mesh-edge-select'],6);
assert.equal(audit.by_family['mesh-edit'],1);
assert.equal(Platform.creativeHands.audit().total,314);
assert.equal(Platform.creativeHands.recipeRegistry().count,321);

const plane=gridMesh(4);assert.equal(plane.indices.length/3,32);
const all=EditHands.invoke('creative.mesh-face-select.all',{mesh:plane}).result;assert.equal(all.faces.length,32);
const indexed=EditHands.invoke('creative.mesh-face-select.indices',{mesh:plane,faces:[0,1]}).result;assert.deepEqual(indexed.faces,[0,1]);
const byNormal=EditHands.invoke('creative.mesh-face-select.by-normal',{mesh:plane,spec:{direction:[0,1,0],min_dot:.99}}).result;assert.equal(byNormal.faces.length,32);
const byAxis=EditHands.invoke('creative.mesh-face-select.by-axis',{mesh:plane,spec:{axis:'y',side:'positive',threshold:0}}).result;assert.equal(byAxis.faces.length,32);
const byArea=EditHands.invoke('creative.mesh-face-select.by-area',{mesh:plane,spec:{min:0,max:1}}).result;assert.equal(byArea.faces.length,32);
const boundaryFaces=EditHands.invoke('creative.mesh-face-select.boundary',{mesh:plane}).result;assert(boundaryFaces.faces.length>0&&boundaryFaces.faces.length<32);
const connected=EditHands.invoke('creative.mesh-face-select.connected',{mesh:plane,seed_face:0}).result;assert.equal(connected.faces.length,32);

const vIndexed=EditHands.invoke('creative.mesh-vertex-select.indices',{mesh:plane,vertices:[0,1,2]}).result;assert.deepEqual(vIndexed.vertices,[0,1,2]);
const vBox=EditHands.invoke('creative.mesh-vertex-select.box',{mesh:plane,spec:{min:[-.6,-.1,-.6],max:[.6,.1,.6]}}).result;assert(vBox.vertices.length>1);
const vSphere=EditHands.invoke('creative.mesh-vertex-select.sphere',{mesh:plane,spec:{center:[0,0,0],radius:.1}}).result;assert.equal(vSphere.vertices.length,1);
const vAxis=EditHands.invoke('creative.mesh-vertex-select.by-axis',{mesh:plane,spec:{axis:'y',side:'positive',threshold:0}}).result;assert.equal(vAxis.vertices.length,plane.positions.length/3);
const vNormal=EditHands.invoke('creative.mesh-vertex-select.by-normal',{mesh:plane,spec:{direction:[0,1,0],min_dot:.99}}).result;assert.equal(vNormal.vertices.length,plane.positions.length/3);

const expanded=EditHands.invoke('creative.mesh-selection.expand-faces',{mesh:plane,selection:indexed,steps:1}).result;assert(expanded.faces.length>indexed.faces.length);
const shrunk=EditHands.invoke('creative.mesh-selection.shrink-faces',{mesh:plane,selection:all,steps:1}).result;assert(shrunk.faces.length>0&&shrunk.faces.length<all.faces.length);assert.equal(shrunk.meta.boundary_aware,true);
const inverted=EditHands.invoke('creative.mesh-selection.invert-faces',{mesh:plane,selection:indexed}).result;assert.equal(inverted.faces.length,30);
const faceVertices=EditHands.invoke('creative.mesh-selection.faces-to-vertices',{mesh:plane,selection:indexed}).result;assert.equal(faceVertices.vertices.length,4);
const invertedVertices=EditHands.invoke('creative.mesh-selection.invert-vertices',{mesh:plane,selection:vIndexed}).result;assert.equal(invertedVertices.vertices.length,plane.positions.length/3-3);

const allEdges=EditHands.invoke('creative.mesh-edge-select.all',{mesh:plane}).result;
const boundaryEdges=EditHands.invoke('creative.mesh-edge-select.boundary',{mesh:plane}).result;assert(allEdges.edges.length>boundaryEdges.edges.length&&boundaryEdges.edges.length>0);
const edgeIndices=EditHands.invoke('creative.mesh-edge-select.indices',{mesh:plane,edges:boundaryEdges.edges.slice(0,2)}).result;assert.equal(edgeIndices.edges.length,2);
const edgeVertices=EditHands.invoke('creative.mesh-selection.edges-to-vertices',{mesh:plane,selection:edgeIndices}).result;assert(edgeVertices.vertices.length>=2);
const vertexFaces=EditHands.invoke('creative.mesh-selection.vertices-to-faces',{mesh:plane,selection:vIndexed}).result;assert(vertexFaces.faces.length>0);
const lengthEdges=EditHands.invoke('creative.mesh-edge-select.by-length',{mesh:plane,spec:{min:.1,max:1}}).result;assert(lengthEdges.edges.length>0);
const regionBoundary=EditHands.invoke('creative.mesh-edge-select.region-boundary',{mesh:plane,selection:indexed}).result;assert.equal(regionBoundary.edges.length,4);

const cube=MeshHands.invoke('creative.mesh-primitive.cube',{spec:{id:'cube',detail:8}}).result;
const welded=Mesh.weld(cube,1e-6);
const sharp=EditHands.invoke('creative.mesh-edge-select.by-angle',{mesh:welded,spec:{min_degrees:45}}).result;assert(sharp.edges.length>0);

const one=EditHands.invoke('creative.mesh-face-select.indices',{mesh:plane,faces:[0]}).result;
const deleted=EditHands.invoke('creative.mesh-face-edit.delete',{mesh:plane,selection:one}).result;assert.equal(deleted.indices.length/3,31);
const flipped=EditHands.invoke('creative.mesh-face-edit.flip',{mesh:plane,selection:one}).result;assert.equal(flipped.indices[1],plane.indices[2]);assert.equal(flipped.indices[2],plane.indices[1]);
const extracted=EditHands.invoke('creative.mesh-face-edit.extract',{mesh:plane,selection:indexed,id:'extract'}).result;assert.equal(extracted.indices.length/3,2);
const duplicated=EditHands.invoke('creative.mesh-face-edit.duplicate',{mesh:plane,selection:one,spec:{offset:[0,1,0]}}).result;assert.equal(duplicated.indices.length/3,33);
const regionExtrude=EditHands.invoke('creative.mesh-face-edit.extrude-region',{mesh:plane,selection:indexed,spec:{distance:.25,direction:[0,1,0]}}).result;assert.equal(regionExtrude.indices.length/3,40);
const individual=EditHands.invoke('creative.mesh-face-edit.extrude-individual',{mesh:plane,selection:one,spec:{distance:.25}}).result;assert.equal(individual.indices.length/3,38);
const inset=EditHands.invoke('creative.mesh-face-edit.inset-individual',{mesh:plane,selection:one,amount:.25}).result;assert.equal(inset.indices.length/3,38);
const closedAll=EditHands.invoke('creative.mesh-face-select.all',{mesh:welded}).result;assert.throws(()=>EditHands.invoke('creative.mesh-face-edit.extrude-region',{mesh:welded,selection:closedAll,spec:{distance:.1}}),/no boundary/);

const translated=EditHands.invoke('creative.mesh-vertex-edit.translate',{mesh:plane,selection:vBox,vector:[0,.2,0]}).result;assert.notEqual(translated.digest,plane.digest);
const scaled=EditHands.invoke('creative.mesh-vertex-edit.scale',{mesh:plane,selection:vBox,factor:.8}).result;assert.notEqual(scaled.digest,plane.digest);
for(const axis of ['x','y','z'])assert.notEqual(EditHands.invoke('creative.mesh-vertex-edit.rotate-'+axis,{mesh:plane,selection:vBox,degrees:30}).result.digest,plane.digest);
const corner=EditHands.invoke('creative.mesh-vertex-select.indices',{mesh:plane,vertices:[0]}).result;
const smoothed=EditHands.invoke('creative.mesh-vertex-edit.smooth',{mesh:plane,selection:corner,spec:{factor:.5,iterations:1}}).result;assert.notEqual(smoothed.digest,plane.digest);
const noiseA=EditHands.invoke('creative.mesh-vertex-edit.noise',{mesh:plane,selection:vBox,spec:{amount:.05,seed:'same'}}).result,noiseB=EditHands.invoke('creative.mesh-vertex-edit.noise',{mesh:plane,selection:vBox,spec:{amount:.05,seed:'same'}}).result;assert.equal(noiseA.digest,noiseB.digest);
assert.throws(()=>EditHands.invoke('creative.mesh-face-edit.delete',{mesh:translated,selection:one}),/selection must bind exact mesh/);

const split=EditHands.invoke('creative.mesh-edit.split-face-vertices',{mesh:plane}).result;assert.equal(split.positions.length/3,split.indices.length);assert.equal(split.indices.length/3,32);
const recipe=Platform.creativeHands.invokeRecipe('mesh-face-edit.extrude-region',{mesh:plane,selection:indexed,spec:{distance:.2,direction:[0,1,0]}});assert.equal(recipe.state,'EXECUTABLE');assert.equal(recipe.result.result.schema,Mesh.SCHEMA);
console.log(JSON.stringify({status:'PASS',edit_hands:audit.total,public_hands:Platform.creativeHands.audit().total,recipes:Platform.creativeHands.recipeRegistry().count,grid:plane.digest,extrude:regionExtrude.digest,split:split.digest,sharp_edges:sharp.edges.length},null,2));