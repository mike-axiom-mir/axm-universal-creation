'use strict';
const assert=require('assert');
const Mesh=require('./precision-mesh');
const Edit=require('./creative-mesh-edit-hands');
const mesh=Mesh.create({id:'edge-contract',positions:[0,0,0,1,0,0,0,1,0,2,0,0],uvs:[0,0,1,0,0,1,1,1],indices:[0,1,2]});
const edge=Edit.invoke('creative.mesh-edge-select.indices',{mesh,edges:[[0,1]]});
assert.deepEqual(edge.result.edges,['0:1']);
assert.throws(()=>Edit.invoke('creative.mesh-edge-select.indices',{mesh,edges:[[0,3]]}),/non-edge pair/);
console.log(JSON.stringify({status:'PASS',edge:edge.digest},null,2));