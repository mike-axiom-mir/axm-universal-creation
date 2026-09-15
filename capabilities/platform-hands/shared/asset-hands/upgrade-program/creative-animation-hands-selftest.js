'use strict';
const assert=require('assert');
const Hands=require('./creative-animation-hands');
const Platform=require('../../../index');
const Flow=require('./creative-flow');
const Mesh=require('./precision-mesh');

function skeletonSpec(){return{id:'humanoid-mini',bones:[
 {id:'root',parent:null,rest:{translation:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}},
 {id:'upper',parent:'root',rest:{translation:[0,1,0],rotation:[0,0,0,1],scale:[1,1,1]}},
 {id:'lower',parent:'upper',rest:{translation:[0,1,0],rotation:[0,0,0,1],scale:[1,1,1]}},
 {id:'hand',parent:'lower',rest:{translation:[0,1,0],rotation:[0,0,0,1],scale:[1,1,1]}}
]};}
function baseClipSpec(){const s=Math.SQRT1_2;return{id:'walk-mini',duration:2,tracks:[
 {id:'root-t',bone:'root',property:'translation',interpolation:'linear',keys:[{time:0,value:[0,0,0]},{time:2,value:[2,0,0]}]},
 {id:'upper-r',bone:'upper',property:'rotation',interpolation:'smoothstep',keys:[{time:0,value:[0,0,0,1]},{time:2,value:[0,0,s,s]}]}
]};}
const audit=Hands.audit();assert.equal(audit.total,48);assert.equal(audit.by_family['rig-skeleton'],9);assert.equal(audit.by_family['rig-pose'],11);assert.equal(audit.by_family['rig-skin'],8);assert.equal(audit.by_family['animation-blendshape'],6);assert.equal(audit.by_family['animation-clip'],13);assert.equal(audit.by_family['rig-ik'],1);assert(Platform.creativeHands.audit().total>=388);assert(Platform.creativeHands.recipeRegistry().count>=395);assert(Flow.summary().public_hands>=388);assert(Flow.summary().callable_recipes>=395);

const sk=Hands.invoke('creative.rig-skeleton.create',{spec:skeletonSpec()}).result;assert.equal(sk.schema,'axm.precision-skeleton/v1');assert.equal(sk.bones.length,4);
const plus=Hands.invoke('creative.rig-skeleton.add-bone',{skeleton:sk,spec:{id:'finger',parent:'hand',rest:{translation:[0,.3,0]}}}).result;assert.equal(plus.bones.length,5);
const removed=Hands.invoke('creative.rig-skeleton.remove-leaf',{skeleton:plus,id:'finger'}).result;assert.equal(removed.bones.length,4);
const renamed=Hands.invoke('creative.rig-skeleton.rename-bone',{skeleton:sk,old_id:'hand',new_id:'wrist'}).result;assert(renamed.bones.some((b)=>b.id==='wrist'));
const reparented=Hands.invoke('creative.rig-skeleton.reparent',{skeleton:sk,id:'hand',parent:'upper'}).result;assert.equal(reparented.bones.find((b)=>b.id==='hand').parent,'upper');
const restChanged=Hands.invoke('creative.rig-skeleton.set-rest',{skeleton:sk,id:'lower',transform:{translation:[0,1.2,0],rotation:[0,0,0,1],scale:[1,1,1]}}).result;assert.equal(restChanged.bones.find((b)=>b.id==='lower').rest.translation[1],1.2);
const restWorld=Hands.invoke('creative.rig-skeleton.world-rest',{skeleton:sk}).result;assert.equal(Object.keys(restWorld.matrices).length,4);assert(Math.abs(restWorld.matrices.hand[13]-3)<1e-9);
const chain=Hands.invoke('creative.rig-skeleton.chain',{skeleton:sk,spec:{start:'root',end:'hand'}}).result;assert.deepEqual(chain.bones,['root','upper','lower','hand']);
const skValid=Hands.invoke('creative.rig-skeleton.validate',{skeleton:sk}).result;assert.equal(skValid.status,'PASS');

const basePose=Hands.invoke('creative.rig-pose.create',{skeleton:sk}).result;assert.equal(basePose.schema,'axm.precision-pose/v1');
const setPose=Hands.invoke('creative.rig-pose.set-transform',{skeleton:sk,pose:basePose,id:'root',transform:{translation:[2,0,0],rotation:[0,0,0,1],scale:[1,1,1]}}).result;assert.equal(setPose.locals.root.translation[0],2);
const translated=Hands.invoke('creative.rig-pose.translate',{skeleton:sk,pose:basePose,id:'upper',vector:[.5,0,0]}).result;assert.equal(translated.locals.upper.translation[0],.5);
const rotated=Hands.invoke('creative.rig-pose.rotate-euler',{skeleton:sk,pose:basePose,id:'upper',euler:[0,0,45]}).result;assert.notDeepEqual(rotated.locals.upper.rotation,[0,0,0,1]);
const quat=Hands.invoke('creative.rig-pose.rotate-quaternion',{skeleton:sk,pose:basePose,id:'lower',quaternion:[Math.SQRT1_2,0,0,Math.SQRT1_2]}).result;assert.notDeepEqual(quat.locals.lower.rotation,[0,0,0,1]);
const scaled=Hands.invoke('creative.rig-pose.scale',{skeleton:sk,pose:basePose,id:'lower',vector:[1,1.2,1]}).result;assert.equal(scaled.locals.lower.scale[1],1.2);
const reset=Hands.invoke('creative.rig-pose.reset-bone',{skeleton:sk,pose:rotated,id:'upper'}).result;assert.deepEqual(reset.locals.upper,sk.bones.find((b)=>b.id==='upper').rest);
const copied=Hands.invoke('creative.rig-pose.copy-bone',{skeleton:sk,pose:setPose,source:'root',target:'hand'}).result;assert.deepEqual(copied.locals.hand,setPose.locals.root);
const blended=Hands.invoke('creative.rig-pose.blend',{skeleton:sk,a:basePose,b:setPose,factor:.5}).result;assert.equal(blended.locals.root.translation[0],1);
const poseWorld=Hands.invoke('creative.rig-pose.world-matrices',{skeleton:sk,pose:translated}).result;assert.equal(Object.keys(poseWorld.matrices).length,4);
const limited=Hands.invoke('creative.rig-pose.limit-translation',{skeleton:sk,pose:setPose,id:'root',spec:{min:[-1,-1,-1],max:[1,1,1]}}).result;assert.equal(limited.locals.root.translation[0],1);

const mesh=Platform.creativeHands.invoke('creative.mesh-primitive.cube',{spec:{id:'rig-cube',detail:8}}).result,vc=mesh.positions.length/3;
const looseWeights=Array.from({length:vc},()=>[{bone:'root',weight:.2},{bone:'upper',weight:.3}]);
const skin=Hands.invoke('creative.rig-skin.create',{mesh,skeleton:sk,spec:{weights:looseWeights}}).result;assert.equal(skin.schema,'axm.precision-skin/v1');
const normalized=Hands.invoke('creative.rig-skin.normalize',{mesh,skeleton:sk,skin}).result;assert(normalized.weights.every((row)=>Math.abs(row.reduce((a,x)=>a+x.weight,0)-1)<1e-9));
const pruned=Hands.invoke('creative.rig-skin.prune',{mesh,skeleton:sk,skin:normalized,threshold:.5}).result;assert(pruned.weights.every((row)=>row.length===1));
const limitedSkin=Hands.invoke('creative.rig-skin.limit-influences',{mesh,skeleton:sk,skin:normalized,max:1}).result;assert(limitedSkin.weights.every((row)=>row.length===1));
const vertexSet=Hands.invoke('creative.rig-skin.set-vertex',{mesh,skeleton:sk,skin:normalized,index:0,influences:[{bone:'root',weight:1}]}).result;assert.deepEqual(vertexSet.weights[0],[{bone:'root',weight:1}]);
const nearest=Hands.invoke('creative.rig-skin.nearest-bind',{mesh,skeleton:sk}).result;assert(nearest.weights.every((row)=>row.length===1&&Math.abs(row[0].weight-1)<1e-9));
const skinValid=Hands.invoke('creative.rig-skin.validate',{mesh,skeleton:sk,skin:normalized}).result;assert.equal(skinValid.status,'PASS');
const deformed=Hands.invoke('creative.rig-skin.deform',{mesh,skeleton:sk,skin:normalized,pose:translated}).result;assert.equal(deformed.schema,Mesh.SCHEMA);assert.notEqual(deformed.digest,mesh.digest);

const deltas=mesh.positions.map((_,i)=>i%3===1?.1:0),zero=mesh.positions.map(()=>0),side=mesh.positions.map((_,i)=>i%3===0?.05:0);
const shapes=Hands.invoke('creative.animation-blendshape.create',{mesh,spec:{shapes:[{name:'raise',deltas}]}}).result;assert.equal(shapes.shapes.length,1);
const plusShape=Hands.invoke('creative.animation-blendshape.add-shape',{mesh,set:shapes,spec:{name:'side',deltas:side}}).result;assert.equal(plusShape.shapes.length,2);
const removedShape=Hands.invoke('creative.animation-blendshape.remove-shape',{mesh,set:plusShape,name:'side'}).result;assert.equal(removedShape.shapes.length,1);
const replacedShape=Hands.invoke('creative.animation-blendshape.set-deltas',{mesh,set:shapes,name:'raise',deltas:side}).result;assert.equal(replacedShape.shapes[0].deltas[0],.05);
const scaledShape=Hands.invoke('creative.animation-blendshape.scale-shape',{mesh,set:shapes,name:'raise',factor:2}).result;assert(Math.abs(scaledShape.shapes[0].deltas[1]-.2)<1e-9);
const morphed=Hands.invoke('creative.animation-blendshape.apply',{mesh,set:shapes,weights:{raise:1}}).result;assert.notEqual(morphed.digest,mesh.digest);
const deformedMorph=Hands.invoke('creative.rig-skin.deform',{mesh,skeleton:sk,skin:normalized,pose:basePose,blendshape_set:shapes,blendshape_weights:{raise:1}}).result;assert.notEqual(deformedMorph.digest,mesh.digest);

const clip=Hands.invoke('creative.animation-clip.create',{skeleton:sk,spec:baseClipSpec()}).result;assert.equal(clip.schema,'axm.precision-animation-clip/v1');assert.equal(clip.tracks.length,2);
const addedTrack=Hands.invoke('creative.animation-clip.add-track',{skeleton:sk,clip,track:{id:'lower-t',bone:'lower',property:'translation',keys:[{time:0,value:[0,1,0]},{time:2,value:[0,1.1,0]}]}}).result;assert.equal(addedTrack.tracks.length,3);
const removedTrack=Hands.invoke('creative.animation-clip.remove-track',{skeleton:sk,clip:addedTrack,id:'lower-t'}).result;assert.equal(removedTrack.tracks.length,2);
const keyed=Hands.invoke('creative.animation-clip.set-key',{skeleton:sk,clip,spec:{track_id:'root-t',time:1,value:[1.2,0,0]}}).result;assert.equal(keyed.tracks.find((t)=>t.id==='root-t').keys.length,3);
const deletedKey=Hands.invoke('creative.animation-clip.delete-key',{skeleton:sk,clip:keyed,spec:{track_id:'root-t',time:1}}).result;assert.equal(deletedKey.tracks.find((t)=>t.id==='root-t').keys.length,2);
const inner=Hands.invoke('creative.animation-clip.create',{skeleton:sk,spec:{id:'inner',duration:2,tracks:[{id:'inner-t',bone:'root',property:'translation',keys:[{time:.5,value:[0,0,0]},{time:1.5,value:[1,0,0]}]}]}}).result;
const shifted=Hands.invoke('creative.animation-clip.shift-time',{skeleton:sk,clip:inner,delta:.25}).result;assert.equal(shifted.tracks[0].keys[0].time,.75);
const scaledTime=Hands.invoke('creative.animation-clip.scale-time',{skeleton:sk,clip,factor:2}).result;assert.equal(scaledTime.duration,4);
const trimmed=Hands.invoke('creative.animation-clip.trim',{skeleton:sk,clip,spec:{start:.5,end:1.5}}).result;assert.equal(trimmed.duration,1);assert.equal(trimmed.tracks[0].keys[0].time,0);
const reversed=Hands.invoke('creative.animation-clip.reverse',{skeleton:sk,clip}).result;assert.equal(reversed.tracks[0].keys[0].time,0);
const looped=Hands.invoke('creative.animation-clip.loop',{skeleton:sk,clip,count:2}).result;assert.equal(looped.duration,4);
const concatenated=Hands.invoke('creative.animation-clip.concat',{skeleton:sk,a:clip,b:reversed}).result;assert.equal(concatenated.duration,4);
const sample=Hands.invoke('creative.animation-clip.sample-pose',{skeleton:sk,clip,time:1}).result;assert(Math.abs(sample.pose.locals.root.translation[0]-1)<1e-9);
const baked=Hands.invoke('creative.animation-clip.bake-poses',{skeleton:sk,clip,spec:{fps:2}}).result;assert.equal(baked.frames.length,5);
const ik=Hands.invoke('creative.rig-ik.two-bone-solve',{spec:{root:[0,0,0],target:[1,1,0],upper_length:1,lower_length:1}}).result;assert.equal(ik.reachable,true);assert(Number.isFinite(ik.shoulder_angle)&&Number.isFinite(ik.elbow_angle));

const flow=Flow.run({mode:'execute',goal:'build, animate and deform a simple rigged mesh',steps:[
 {id:'skeleton',hand_id:'creative.rig-skeleton.create',args:{spec:skeletonSpec()},save_as:'skeleton'},
 {id:'mesh',hand_id:'creative.mesh-primitive.cube',args:{spec:{id:'flow-rig-cube',detail:8}},save_as:'mesh'},
 {id:'clip',hand_id:'creative.animation-clip.create',args:{skeleton:{$state:'skeleton'},spec:baseClipSpec()},save_as:'clip'},
 {id:'sample',hand_id:'creative.animation-clip.sample-pose',args:{skeleton:{$state:'skeleton'},clip:{$state:'clip'},time:1},save_as:'sample'},
 {id:'bind',hand_id:'creative.rig-skin.nearest-bind',args:{mesh:{$state:'mesh'},skeleton:{$state:'skeleton'}},save_as:'skin'},
 {id:'deform',hand_id:'creative.rig-skin.deform',args:{mesh:{$state:'mesh'},skeleton:{$state:'skeleton'},skin:{$state:'skin'},pose:{$state:'sample.pose'}},save_as:'deformed'},
 {id:'bounds',hand_id:'creative.mesh-analysis.bounds',args:{mesh:{$state:'deformed'}},save_as:'bounds'}
]});assert.equal(flow.status,'PASS');assert.equal(flow.receipts.length,7);assert(flow.final_state.bounds.size.every((x)=>x>0));assert.notEqual(flow.final_state.deformed.digest,flow.final_state.mesh.digest);

console.log(JSON.stringify({status:'PASS',animation_hands:audit.total,public_hands:Platform.creativeHands.audit().total,recipes:Platform.creativeHands.recipeRegistry().count,skeleton:sk.digest,skin:deformed.digest,blendshape:morphed.digest,clip:clip.digest,bake:baked.digest,ik:ik.digest,flow:flow.digest},null,2));