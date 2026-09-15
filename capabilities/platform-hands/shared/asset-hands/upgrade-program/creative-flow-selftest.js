'use strict';

const assert=require('assert');
const Flow=require('./creative-flow');
const Platform=require('../../../index');

const summary=Flow.summary();
assert.equal(summary.state,'EXECUTABLE');
assert(summary.public_hands>=314);
assert(summary.callable_recipes>=321);
const publicSummary=Platform.creativeFlow.summary();
assert.equal(publicSummary.state,summary.state);
assert.equal(publicSummary.public_hands,summary.public_hands);
assert.equal(publicSummary.callable_recipes,summary.callable_recipes);
assert.equal(publicSummary.hand_audit_digest,summary.hand_audit_digest);
assert.equal(publicSummary.recipe_registry_digest,summary.recipe_registry_digest);
assert.equal(publicSummary.core_flow_digest,summary.digest);
assert.equal(publicSummary.adaptive_quality,true);
assert.deepEqual(publicSummary.adaptive_modes,['adaptive-plan','adaptive-execute','adaptive-calibrate']);
assert.equal(publicSummary.quality_profiles,1);
assert.notEqual(publicSummary.digest,summary.digest);

const exact=Flow.discover({family:'mesh-transform',operation:'scale',require_unique:true});
assert.equal(exact.status,'MATCHES');
assert.equal(exact.matches.length,1);
assert.equal(exact.matches[0].id,'creative.mesh-transform.scale');
const modeling=Flow.discover({family:'mesh-model-cut',operation:'clip-positive',require_unique:true});
assert.equal(modeling.status,'MATCHES');assert.equal(modeling.matches.length,1);assert.equal(modeling.matches[0].id,'creative.mesh-model-cut.clip-positive');

const broad=Flow.discover({query:'mesh',require_unique:true,limit:20});
assert.equal(broad.status,'HOLD_AMBIGUOUS');
assert(broad.tied_top.length>1);

const proseOnly=Flow.run({mode:'plan',goal:'make a wider cube and inspect its final bounds'});
assert.equal(proseOnly.status,'HOLD_PLAN_REQUIRED');
assert(proseOnly.discovery.matches.length>0);

const request={
  mode:'execute',
  goal:'create a wider cube and inspect its bounds',
  state:{label:'source-state'},
  steps:[
    {id:'make',hand_id:'creative.mesh-primitive.cube',args:{spec:{id:'flow-cube',detail:8}},save_as:'mesh'},
    {id:'scale',selector:{family:'mesh-transform',operation:'scale'},args:{mesh:{$state:'mesh'},vector:[2,1,1]},save_as:'scaled'},
    {id:'bounds',recipe_id:'mesh-analysis.bounds',args:{mesh:{$state:'scaled'}},save_as:'bounds'}
  ],
  expose:{bounds:{$state:'bounds'}}
};
const original=JSON.parse(JSON.stringify(request.state));
const compiled=Flow.compile(request);
assert.equal(compiled.status,'READY');
assert.deepEqual(compiled.order,['make','scale','bounds']);
assert.deepEqual(compiled.steps.find((row)=>row.id==='scale').dependencies,['make']);
assert.deepEqual(compiled.steps.find((row)=>row.id==='bounds').dependencies,['scale']);
const result=Flow.run(request);
assert.equal(result.status,'PASS');
assert.equal(result.candidate_ready,true);
assert.equal(result.source_state_mutated,false);
assert.equal(result.receipts.length,3);
assert(result.receipts.every((row)=>row.status==='PASS'));
assert.deepEqual(request.state,original);
assert.deepEqual(result.final_state.bounds.size,[4,2,2]);
assert.deepEqual(result.outputs.bounds.size,[4,2,2]);
assert.notEqual(result.initial_state_digest,result.final_state_digest);

const cross=Flow.run({
  mode:'execute',
  goal:'turn a plane into a shallow edited model and inspect it',
  steps:[
    {id:'plane',hand_id:'creative.mesh-primitive.plane',args:{spec:{id:'flow-plane',detail:4}},save_as:'mesh'},
    {id:'faces',hand_id:'creative.mesh-face-select.all',args:{mesh:{$state:'mesh'}},save_as:'selection'},
    {id:'extrude',hand_id:'creative.mesh-face-edit.extrude-region',args:{mesh:{$state:'mesh'},selection:{$state:'selection'},spec:{distance:.5,direction:[0,1,0]}},save_as:'extruded'},
    {id:'shear',hand_id:'creative.mesh-modifier.shear',args:{mesh:{$state:'extruded'},spec:{target_axis:'x',source_axis:'y',factor:.25}},save_as:'model'},
    {id:'inspect',hand_id:'creative.mesh-analysis.bounds',args:{mesh:{$state:'model'}},save_as:'bounds'}
  ]
});
assert.equal(cross.status,'PASS');
assert.equal(cross.receipts.length,5);
assert.deepEqual(cross.receipts.map((row)=>row.operation_id),[
  'creative.mesh-primitive.plane',
  'creative.mesh-face-select.all',
  'creative.mesh-face-edit.extrude-region',
  'creative.mesh-modifier.shear',
  'creative.mesh-analysis.bounds'
]);
assert(Math.abs(cross.final_state.bounds.size[1]-.5)<1e-9);

const failure=Flow.run({
  mode:'execute',
  state:{label:'source'},
  steps:[
    {id:'make',hand_id:'creative.mesh-primitive.cube',args:{spec:{id:'bad-cube',detail:8}},save_as:'mesh'},
    {id:'bad-scale',hand_id:'creative.mesh-transform.scale',args:{mesh:{$state:'mesh'},vector:[-1,1,1]},save_as:'scaled'}
  ]
});
assert.equal(failure.status,'HOLD_EXECUTION_FAILED');
assert.equal(failure.candidate_ready,false);
assert.equal(failure.source_state_mutated,false);
assert.equal(failure.receipts.length,1);
assert.equal(failure.failure.step_id,'bad-scale');
assert(!Object.prototype.hasOwnProperty.call(failure,'final_state'));

assert.throws(()=>Flow.compile({steps:[
  {id:'a',hand_id:'creative.mesh-primitive.cube',depends_on:['b'],args:{spec:{id:'a',detail:8}}},
  {id:'b',hand_id:'creative.mesh-primitive.cube',depends_on:['a'],args:{spec:{id:'b',detail:8}}}
]}),/dependency cycle/);
assert.throws(()=>Flow.compile({state:{mesh:{x:1}},steps:[
  {id:'overwrite',hand_id:'creative.mesh-primitive.cube',args:{spec:{id:'x',detail:8}},save_as:'mesh'}
]}),/cannot overwrite initial state/);

console.log(JSON.stringify({status:'PASS',summary:summary.digest,public_summary:publicSummary.digest,plan:compiled.digest,result:result.digest,cross:cross.digest,modeling_discovery:modeling.digest,receipts:result.receipts.map((row)=>row.digest),failure:failure.failure.digest},null,2));