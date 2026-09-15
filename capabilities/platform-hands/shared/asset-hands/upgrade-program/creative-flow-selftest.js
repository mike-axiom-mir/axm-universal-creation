'use strict';

const assert=require('assert');
const Flow=require('./creative-flow');
const Platform=require('../../../index');

const summary=Flow.summary();
assert.equal(summary.state,'EXECUTABLE');
assert.equal(summary.public_hands,314);
assert.equal(summary.callable_recipes,321);
assert.equal(Platform.creativeFlow.summary().digest,summary.digest);

const exact=Flow.discover({family:'mesh-transform',operation:'scale',require_unique:true});
assert.equal(exact.status,'MATCHES');
assert.equal(exact.matches.length,1);
assert.equal(exact.matches[0].id,'creative.mesh-transform.scale');

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

console.log(JSON.stringify({status:'PASS',summary:summary.digest,plan:compiled.digest,result:result.digest,receipts:result.receipts.map((row)=>row.digest),failure:failure.failure.digest},null,2));
