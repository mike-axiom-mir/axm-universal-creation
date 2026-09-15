'use strict';
const assert=require('assert');const Hands=require('./creative-animation-hands');const Platform=require('../../../index');
function sk(){return Hands.invoke('creative.rig-skeleton.create',{spec:{id:'contract',bones:[{id:'root',parent:null,rest:{translation:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}},{id:'child',parent:'root',rest:{translation:[0,1,0],rotation:[0,0,0,1],scale:[1,1,1]}}]}}).result;}
assert.throws(()=>Hands.invoke('creative.rig-skeleton.create',{spec:{id:'bad-scale',bones:[{id:'root',parent:null,rest:{scale:[1,0,1]}}]}}),/scale components must be finite and nonzero/);
assert.throws(()=>Hands.invoke('creative.rig-skeleton.create',{spec:{id:'cycle',bones:[{id:'a',parent:'b'},{id:'b',parent:'a'}]}}),/parent cycle/);
assert.throws(()=>Hands.invoke('creative.rig-ik.two-bone-solve',{spec:{root:[0,0,0],target:[1,0,0],upper_length:0,lower_length:1}}),/segment lengths must be positive/);
const skeleton=sk();
assert.throws(()=>Hands.invoke('creative.animation-clip.create',{skeleton,spec:{id:'dup',duration:1,tracks:[{id:'a',bone:'root',property:'translation',keys:[{time:0,value:[0,0,0]}]},{id:'b',bone:'root',property:'translation',keys:[{time:1,value:[1,0,0]}]}]}}),/duplicate bone\/property track/);
const longClip=Hands.invoke('creative.animation-clip.create',{skeleton,spec:{id:'long',duration:100,tracks:[{id:'r',bone:'root',property:'translation',keys:[{time:0,value:[0,0,0]},{time:100,value:[1,0,0]}]}]}}).result;
assert.throws(()=>Hands.invoke('creative.animation-clip.bake-poses',{skeleton,clip:longClip,spec:{fps:240}}),/bake frame budget exceeded/);
const mesh=Platform.creativeHands.invoke('creative.mesh-primitive.cube',{spec:{id:'morph-contract',detail:8}}).result,deltas=mesh.positions.map(()=>0),set=Hands.invoke('creative.animation-blendshape.create',{mesh,spec:{shapes:[{name:'known',deltas}]}}).result;
assert.throws(()=>Hands.invoke('creative.animation-blendshape.apply',{mesh,set,weights:{unknown:1}}),/unknown blendshape weight/);
console.log(JSON.stringify({status:'PASS',contract:'rig-animation-fail-closed',skeleton:skeleton.digest,clip:longClip.digest,set:set.digest},null,2));