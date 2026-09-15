'use strict';

const U=require('./foundation-utils');
const Flow=require('./creative-flow');
const CreativeHands=require('../creative-hands-service');

const SCHEMA='axm.creative-quality-gauntlet/v1';
const GOAL='Create one game-ready animated armored sci-fi supply crate while preserving editable geometry, UV, material and animation state.';
const LEVELS=Object.freeze(['draft','game-ready','production','max-current-body']);

function step(id,hand_id,args,save_as){return{id,hand_id,args:args||{},save_as:save_as||id};}
function geometrySteps(){return[
 step('body','creative.mesh-primitive.cube',{spec:{id:'crate-body',detail:8}}),
 step('body-scale','creative.mesh-transform.scale',{mesh:{$state:'body'},vector:[2.4,.9,1.5]},'bodyScaled'),
 step('lid','creative.mesh-primitive.cube',{spec:{id:'crate-lid',detail:8}}),
 step('lid-scale','creative.mesh-transform.scale',{mesh:{$state:'lid'},vector:[2.45,.25,1.55]},'lidScaled'),
 step('lid-position','creative.mesh-transform.translate',{mesh:{$state:'lidScaled'},vector:[0,1.15,0]},'lidPlaced'),
 step('rail-left','creative.mesh-primitive.cube',{spec:{id:'crate-rail-left',detail:8}}),
 step('rail-left-scale','creative.mesh-transform.scale',{mesh:{$state:'rail-left'},vector:[.14,1.1,1.62]},'railLeftScaled'),
 step('rail-left-position','creative.mesh-transform.translate',{mesh:{$state:'railLeftScaled'},vector:[-2.25,.1,0]},'railLeft'),
 step('rail-right','creative.mesh-primitive.cube',{spec:{id:'crate-rail-right',detail:8}}),
 step('rail-right-scale','creative.mesh-transform.scale',{mesh:{$state:'rail-right'},vector:[.14,1.1,1.62]},'railRightScaled'),
 step('rail-right-position','creative.mesh-transform.translate',{mesh:{$state:'railRightScaled'},vector:[2.25,.1,0]},'railRight'),
 step('latch','creative.mesh-primitive.cube',{spec:{id:'crate-latch',detail:8}}),
 step('latch-scale','creative.mesh-transform.scale',{mesh:{$state:'latch'},vector:[.35,.4,.12]},'latchScaled'),
 step('latch-position','creative.mesh-transform.translate',{mesh:{$state:'latchScaled'},vector:[0,.25,-1.62]},'latchPlaced'),
 step('assemble','creative.mesh-topology.merge',{meshes:[{$state:'bodyScaled'},{$state:'lidPlaced'},{$state:'railLeft'},{$state:'railRight'},{$state:'latchPlaced'}],id:'armored-crate'},'mesh'),
 step('normals','creative.mesh-topology.recalc-normals',{mesh:{$state:'mesh'}},'model'),
 step('bounds','creative.mesh-analysis.bounds',{mesh:{$state:'model'}},'bounds'),
 step('topology','creative.mesh-analysis.topology',{mesh:{$state:'model'}},'topology')
];}
function uvMaterialSteps(){return[
 step('uv-create','creative.uv-production.create',{mesh:{$state:'model'}},'uv'),
 step('uv-seams','creative.uv-production.mark-sharp-seams',{mesh:{$state:'model'},layout:{$state:'uv'},spec:{degrees:45}},'seamedUv'),
 step('uv-project','creative.uv-production.project-all',{mesh:{$state:'model'},layout:{$state:'seamedUv'}},'projectedUv'),
 step('uv-pack','creative.uv-production.pack',{mesh:{$state:'model'},layout:{$state:'projectedUv'},spec:{padding:.03}},'packedUv'),
 step('base-colour','creative.procedural.solid',{spec:{width:64,height:64,rgba:[58,68,78,255]}},'baseColour'),
 step('roughness','creative.procedural.solid',{spec:{width:64,height:64,rgba:[165,165,165,255]}},'roughness'),
 step('metallic','creative.procedural.solid',{spec:{width:64,height:64,rgba:[190,190,190,255]}},'metallic'),
 step('ao','creative.procedural.solid',{spec:{width:64,height:64,rgba:[235,235,235,255]}},'ao'),
 step('height','creative.procedural.checker',{spec:{width:64,height:64,size:8,a_rgba:[105,105,105,255],b_rgba:[135,135,135,255]}},'height'),
 step('material','creative.material.create',{spec:{id:'armored-crate-material',channels:{'base-colour':{$state:'baseColour'},roughness:{$state:'roughness'},metallic:{$state:'metallic'},ao:{$state:'ao'},height:{$state:'height'}}}},'material'),
 step('material-normal','creative.material.normal-from-height',{material:{$state:'material'},spec:{strength:3}},'materialNormal'),
 step('orm','creative.material.pack-orm',{material:{$state:'materialNormal'}},'orm'),
 step('uv-normal-evidence','creative.texture-projection.normal-map',{mesh:{$state:'model'},layout:{$state:'packedUv'},spec:{width:64,height:64}},'uvNormalEvidence'),
 step('surface-area','creative.mesh-analysis.surface-area',{mesh:{$state:'model'}},'surfaceArea')
];}
function maxDetailSteps(){
 const angle=-55*Math.PI/180,q=[Math.sin(angle/2),0,0,Math.cos(angle/2)];
 return[
  step('stack','creative.material-stack.create',{base_material:{$state:'materialNormal'},spec:{id:'armored-crate-stack'}},'stack'),
  step('stack-noise','creative.material-generator.add-procedural',{stack:{$state:'stack'},spec:{id:'surface-noise',channel:'base-colour',generator:'noise',generator_spec:{seed:'crate-surface'},blend:'soft-light',opacity:.22}},'stackNoise'),
  step('stack-rough','creative.material-generator.add-fill',{stack:{$state:'stackNoise'},spec:{id:'rough-edge',channels:{roughness:[215,215,215,255]},opacity:.3}},'stackRough'),
  step('scratch-mask','creative.material-generator.scratch-mask',{stack:{$state:'stackRough'},spec:{count:12,length:18,seed:'crate-scratches'}},'scratchMask'),
  step('mask-noise','creative.material-stack.set-mask',{stack:{$state:'stackRough'},spec:{id:'surface-noise',mask:{$state:'scratchMask'}}},'maskedStack'),
  step('flatten-material','creative.material-stack.flatten',{stack:{$state:'maskedStack'}},'finishedMaterial'),
  step('skeleton','creative.rig-skeleton.create',{spec:{id:'crate-rig',bones:[{id:'root',parent:null,rest:{translation:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}},{id:'lid',parent:'root',rest:{translation:[0,1.15,0],rotation:[0,0,0,1],scale:[1,1,1]}}]}},'skeleton'),
  step('skin','creative.rig-skin.nearest-bind',{mesh:{$state:'model'},skeleton:{$state:'skeleton'}},'skin'),
  step('skin-valid','creative.rig-skin.validate',{mesh:{$state:'model'},skeleton:{$state:'skeleton'},skin:{$state:'skin'}},'skinValidation'),
  step('clip','creative.animation-clip.create',{skeleton:{$state:'skeleton'},spec:{id:'crate-open',duration:1,tracks:[{id:'lid-rotation',bone:'lid',property:'rotation',interpolation:'smoothstep',keys:[{time:0,value:[0,0,0,1]},{time:1,value:q}]}]}},'clip'),
  step('pose','creative.animation-clip.sample-pose',{skeleton:{$state:'skeleton'},clip:{$state:'clip'},time:.75},'poseSample'),
  step('bake','creative.animation-clip.bake-poses',{skeleton:{$state:'skeleton'},clip:{$state:'clip'},spec:{fps:8}},'baked'),
  step('deform','creative.rig-skin.deform',{mesh:{$state:'model'},skeleton:{$state:'skeleton'},skin:{$state:'skin'},pose:{$state:'poseSample.pose'}},'deformed'),
  step('animated-bounds','creative.mesh-analysis.bounds',{mesh:{$state:'deformed'}},'animatedBounds'),
  step('animated-topology','creative.mesh-analysis.topology',{mesh:{$state:'deformed'}},'animatedTopology')
 ];
}
function build(level){
 U.ensure(LEVELS.includes(level),'unknown gauntlet quality level: '+level);
 let steps;
 if(level==='draft')steps=[geometrySteps()[0],geometrySteps()[1],step('draft-bounds','creative.mesh-analysis.bounds',{mesh:{$state:'bodyScaled'}},'bounds')];
 else if(level==='game-ready')steps=geometrySteps();
 else if(level==='production')steps=geometrySteps().concat(uvMaterialSteps());
 else steps=geometrySteps().concat(uvMaterialSteps(),maxDetailSteps());
 return{mode:'execute',goal:GOAL,steps};
}
function exactSurfaceGaps(){const catalog=Flow.catalog();const has=(predicate)=>catalog.some(predicate);return[
 {id:'hard-surface-bevel',available:has((h)=>h.family.includes('mesh')&&h.operation.includes('bevel')),scope:'public Creative Hands exact advertised operation'},
 {id:'general-mesh-boolean',available:has((h)=>h.family.includes('mesh')&&h.operation.includes('boolean')),scope:'public Creative Hands exact advertised operation'},
 {id:'animation-retarget',available:has((h)=>h.operation.includes('retarget')),scope:'public Creative Hands exact advertised operation'},
 {id:'optical-flow-tracking',available:has((h)=>h.operation.includes('optical')||h.operation.includes('flow-track')),scope:'public Creative Hands exact advertised operation'},
 {id:'spectral-audio-restoration',available:has((h)=>h.family.includes('audio')&&h.operation.includes('spectral')),scope:'public Creative Hands exact advertised operation'},
 {id:'final-render-hand',available:has((h)=>h.operation==='render' || h.operation.includes('render-final')),scope:'public Creative Hands exact advertised operation'}
 ];}
function timingRun(request){const start=process.hrtime.bigint(),result=Flow.run(request),end=process.hrtime.bigint();return{result,elapsed_ms:Number(end-start)/1e6};}
function run(){
 const summary=Flow.summary(),goalOnly=Flow.run({mode:'plan',goal:GOAL}),levels=[];
 for(const level of LEVELS){const request=build(level),timed=timingRun(request),result=timed.result;const ids=result.receipts?result.receipts.map((r)=>r.operation_id):[],families=Array.from(new Set(ids.map((id)=>{const h=CreativeHands.get(id);return h?h.family:'recipe';}))).sort(),stateBytes=result.final_state?Buffer.byteLength(JSON.stringify(result.final_state)):0;levels.push({level,status:result.status,candidate_ready:result.candidate_ready===true,steps:result.receipts?result.receipts.length:0,active_operations:new Set(ids).size,families,state_bytes:stateBytes,final_state_digest:result.final_state_digest||null,elapsed_ms:Math.round(timed.elapsed_ms*1000)/1000,steps_per_ms:timed.elapsed_ms>0?Math.round((ids.length/timed.elapsed_ms)*1000000)/1000000:null});}
 const gaps=exactSurfaceGaps(),structure={schema:SCHEMA,version:'1.0.0',goal:GOAL,public_hands:summary.public_hands,callable_recipes:summary.callable_recipes,goal_only_status:goalOnly.status,levels:levels.map(({elapsed_ms,steps_per_ms,...rest})=>rest),gaps};const value=Object.assign({},structure,{timing_truth:'Wall-clock measurements are observational for the current runtime and are excluded from the structural digest.',timings:levels.map((x)=>({level:x.level,elapsed_ms:x.elapsed_ms,steps_per_ms:x.steps_per_ms}))});value.digest=U.sha256(structure);return value;
}

module.exports={SCHEMA,GOAL,LEVELS,build,run};
