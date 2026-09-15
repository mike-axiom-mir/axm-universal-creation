'use strict';

const U=require('./foundation-utils');

const PROFILE_SCHEMA='axm.creative-quality-profile/v1';
const REGISTRY_SCHEMA='axm.creative-quality-profile-registry/v1';
const QUALITY_ALIASES=Object.freeze({
  draft:.15,
  preview:.2,
  low:.25,
  'game-ready':.45,
  medium:.55,
  production:.72,
  high:.85,
  ultra:.9,
  'max-current-body':.9,
  maximum:1,
  max:1,
});

function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
function tokens(value){return Array.from(new Set(String(value||'').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean))).sort();}
function normalizeQuality(value){
  if(value==null)return QUALITY_ALIASES.production;
  if(typeof value==='string'){
    const key=value.trim().toLowerCase();
    if(Object.prototype.hasOwnProperty.call(QUALITY_ALIASES,key))return QUALITY_ALIASES[key];
    const number=Number(key);U.ensure(Number.isFinite(number),'quality must be 0..1 or a known alias');value=number;
  }
  const q=U.finite(value,'quality');U.ensure(q>=0&&q<=1,'quality outside 0..1');return q;
}
function step(id,hand_id,args,save_as){return{id,hand_id,args:args||{},save_as:save_as||id};}
function textureResolution(q){if(q<.68)return 32;if(q<.88)return 64;if(q<.97)return 128;return 256;}
function detailParameters(q){const t=clamp((q-.85)/.15,0,1);return{scratch_count:Math.round(6+t*18),scratch_length:Math.round(12+t*16),bake_fps:Math.round(6+t*24),texture_resolution:textureResolution(q)};}
function crateDraftSteps(){return[
 step('body','creative.mesh-primitive.cube',{spec:{id:'crate-body',detail:8}}),
 step('body-scale','creative.mesh-transform.scale',{mesh:{$state:'body'},vector:[2.4,.9,1.5]},'bodyScaled'),
 step('draft-bounds','creative.mesh-analysis.bounds',{mesh:{$state:'bodyScaled'}},'bounds')
];}
function crateAssemblySteps(){return[
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
function cratePremiumGeometrySteps(q){if(q<.92)return[];return[
 step('premium-bevel','creative.mesh-model-finish.bevel',{mesh:{$state:'model'},spec:{width:q>=.98?.045:.035,segments:q>=.98?4:3,angle_degrees:45}},'premiumModel')
];}
function meshStateFor(q){return q>=.92?'premiumModel':'model';}
function crateProductionSteps(q){
 const meshName=meshStateFor(q),r=textureResolution(q),padding=q>=.9?.02:q>=.75?.03:.04;
 return[
  step('uv-create','creative.uv-production.create',{mesh:{$state:meshName}},'uv'),
  step('uv-seams','creative.uv-production.mark-sharp-seams',{mesh:{$state:meshName},layout:{$state:'uv'},spec:{degrees:45}},'seamedUv'),
  step('uv-project','creative.uv-production.project-all',{mesh:{$state:meshName},layout:{$state:'seamedUv'}},'projectedUv'),
  step('uv-pack','creative.uv-production.pack',{mesh:{$state:meshName},layout:{$state:'projectedUv'},spec:{padding}},'packedUv'),
  step('base-colour','creative.procedural.solid',{spec:{width:r,height:r,rgba:[58,68,78,255]}},'baseColour'),
  step('roughness','creative.procedural.solid',{spec:{width:r,height:r,rgba:[165,165,165,255]}},'roughness'),
  step('metallic','creative.procedural.solid',{spec:{width:r,height:r,rgba:[190,190,190,255]}},'metallic'),
  step('ao','creative.procedural.solid',{spec:{width:r,height:r,rgba:[235,235,235,255]}},'ao'),
  step('height','creative.procedural.checker',{spec:{width:r,height:r,size:Math.max(4,Math.round(r/8)),a_rgba:[105,105,105,255],b_rgba:[135,135,135,255]}},'height'),
  step('material','creative.material.create',{spec:{id:'armored-crate-material',channels:{'base-colour':{$state:'baseColour'},roughness:{$state:'roughness'},metallic:{$state:'metallic'},ao:{$state:'ao'},height:{$state:'height'}}}},'material'),
  step('material-normal','creative.material.normal-from-height',{material:{$state:'material'},spec:{strength:2.5+q*1.5}},'materialNormal'),
  step('orm','creative.material.pack-orm',{material:{$state:'materialNormal'}},'orm'),
  step('uv-normal-evidence','creative.texture-projection.normal-map',{mesh:{$state:meshName},layout:{$state:'packedUv'},spec:{width:r,height:r}},'uvNormalEvidence'),
  step('surface-area','creative.mesh-analysis.surface-area',{mesh:{$state:meshName}},'surfaceArea')
 ];
}
function crateDetailSteps(q){
 const meshName=meshStateFor(q),p=detailParameters(q),angle=-55*Math.PI/180,quat=[Math.sin(angle/2),0,0,Math.cos(angle/2)];
 return[
  step('stack','creative.material-stack.create',{base_material:{$state:'materialNormal'},spec:{id:'armored-crate-stack'}},'stack'),
  step('stack-noise','creative.material-generator.add-procedural',{stack:{$state:'stack'},spec:{id:'surface-noise',channel:'base-colour',generator:'noise',generator_spec:{seed:'crate-surface'},blend:'soft-light',opacity:.18+q*.08}},'stackNoise'),
  step('stack-rough','creative.material-generator.add-fill',{stack:{$state:'stackNoise'},spec:{id:'rough-edge',channels:{roughness:[215,215,215,255]},opacity:.22+q*.1}},'stackRough'),
  step('scratch-mask','creative.material-generator.scratch-mask',{stack:{$state:'stackRough'},spec:{count:p.scratch_count,length:p.scratch_length,seed:'crate-scratches'}},'scratchMask'),
  step('mask-noise','creative.material-stack.set-mask',{stack:{$state:'stackRough'},spec:{id:'surface-noise',mask:{$state:'scratchMask'}}},'maskedStack'),
  step('flatten-material','creative.material-stack.flatten',{stack:{$state:'maskedStack'}},'finishedMaterial'),
  step('skeleton','creative.rig-skeleton.create',{spec:{id:'crate-rig',bones:[{id:'root',parent:null,rest:{translation:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]}},{id:'lid',parent:'root',rest:{translation:[0,1.15,0],rotation:[0,0,0,1],scale:[1,1,1]}}]}},'skeleton'),
  step('skin','creative.rig-skin.nearest-bind',{mesh:{$state:meshName},skeleton:{$state:'skeleton'}},'skin'),
  step('skin-valid','creative.rig-skin.validate',{mesh:{$state:meshName},skeleton:{$state:'skeleton'},skin:{$state:'skin'}},'skinValidation'),
  step('clip','creative.animation-clip.create',{skeleton:{$state:'skeleton'},spec:{id:'crate-open',duration:1,tracks:[{id:'lid-rotation',bone:'lid',property:'rotation',interpolation:'smoothstep',keys:[{time:0,value:[0,0,0,1]},{time:1,value:quat}]}]}},'clip'),
  step('pose','creative.animation-clip.sample-pose',{skeleton:{$state:'skeleton'},clip:{$state:'clip'},time:.75},'poseSample'),
  step('bake','creative.animation-clip.bake-poses',{skeleton:{$state:'skeleton'},clip:{$state:'clip'},spec:{fps:p.bake_fps}},'baked'),
  step('deform','creative.rig-skin.deform',{mesh:{$state:meshName},skeleton:{$state:'skeleton'},skin:{$state:'skin'},pose:{$state:'poseSample.pose'}},'deformed'),
  step('animated-bounds','creative.mesh-analysis.bounds',{mesh:{$state:'deformed'}},'animatedBounds'),
  step('animated-topology','creative.mesh-analysis.topology',{mesh:{$state:'deformed'}},'animatedTopology')
 ];
}
function crateSteps(q){
 q=normalizeQuality(q);let steps=crateDraftSteps();
 if(q>=.3)steps=crateDraftSteps().slice(0,2).concat(crateAssemblySteps());
 if(q>=.92)steps=steps.concat(cratePremiumGeometrySteps(q));
 if(q>=.6)steps=steps.concat(crateProductionSteps(q));
 if(q>=.85)steps=steps.concat(crateDetailSteps(q));
 return steps;
}
function crateEstimateStateBytes(q){q=normalizeQuality(q);if(q<.3)return 3000;if(q<.6)return 32000;const scale=Math.pow(textureResolution(q)/64,2),production=500000*scale;if(q<.85)return Math.round(32000+production);return Math.round(32000+production+850000*scale+detailParameters(q).bake_fps*2500);}
function crateScore(goal){const set=new Set(tokens(goal));if(!['crate','chest','container'].some((x)=>set.has(x)))return 0;let score=100;for(const term of ['supply','armored','armoured','scifi','sci','fi','game','asset','prop','animated','lid'])if(set.has(term))score+=10;return score;}
const PROFILES=Object.freeze([{id:'game-prop.armored-crate/v1',schema:PROFILE_SCHEMA,version:'1.0.0',title:'Animated armored crate game prop',truth:'Deterministic quality route learned from the verified armored-crate gauntlet. It is not a universal arbitrary-prop planner.',minimum_quality:0,maximum_profile_quality:1,premium_threshold:.92,build:crateSteps,estimateStateBytes:crateEstimateStateBytes,scoreGoal:crateScore}]);
function list(){return PROFILES.map((p)=>({id:p.id,schema:p.schema,version:p.version,title:p.title,truth:p.truth,minimum_quality:p.minimum_quality,maximum_profile_quality:p.maximum_profile_quality,premium_threshold:p.premium_threshold}));}
function get(id){const p=PROFILES.find((x)=>x.id===String(id||''));return p||null;}
function resolve(goal,profileId){if(profileId){const p=get(profileId);return p?{status:'MATCH',profile:p,score:1000}:{status:'HOLD_UNSUPPORTED_PROFILE',profile:null,score:0};}const scored=PROFILES.map((p)=>({profile:p,score:p.scoreGoal(goal)})).filter((x)=>x.score>0).sort((a,b)=>b.score-a.score||a.profile.id.localeCompare(b.profile.id));if(!scored.length)return{status:'HOLD_UNSUPPORTED_GOAL',profile:null,score:0};const top=scored[0].score,ties=scored.filter((x)=>x.score===top);if(ties.length!==1)return{status:'HOLD_AMBIGUOUS_PROFILE',profile:null,score:top,candidates:ties.map((x)=>x.profile.id)};return{status:'MATCH',profile:ties[0].profile,score:top};}
function registry(){const value={schema:REGISTRY_SCHEMA,version:'1.0.0',quality_aliases:QUALITY_ALIASES,profiles:list()};value.digest=U.sha256(value);return value;}
module.exports={PROFILE_SCHEMA,REGISTRY_SCHEMA,QUALITY_ALIASES,normalizeQuality,textureResolution,detailParameters,list,get,resolve,registry};
