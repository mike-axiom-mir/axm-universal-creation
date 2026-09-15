'use strict';

const U=require('./upgrade-program/foundation-utils');
const Flow=require('./upgrade-program/creative-flow');
const Quality=require('./upgrade-program/creative-quality-resolver');

const ADAPTIVE_RESULT_SCHEMA='axm.creative-flow-adaptive-result/v1';
function summary(){const base=Flow.summary(),profiles=Quality.registry(),value=Object.assign({},base,{version:'1.1.0',core_flow_digest:base.digest,adaptive_quality:true,adaptive_modes:['adaptive-plan','adaptive-execute'],quality_profile_registry_digest:profiles.digest,quality_profiles:profiles.profiles.length,adaptive_execution_truth:'Known deterministic quality profiles can author explicit bounded plans from goal + quality + machine budget. Unknown goals still HOLD; current concurrency schedule is planning evidence and execution remains serial.'});value.digest=U.sha256(value);return value;}
function adaptivePlan(request){return Quality.resolve(request||{});}
function adaptiveExecute(request){const resolution=Quality.resolve(request||{});if(!['READY','READY_DEGRADED'].includes(resolution.status)){const value={schema:ADAPTIVE_RESULT_SCHEMA,version:'1.0.0',status:resolution.status,candidate_ready:false,requested_quality:resolution.requested_quality,realized_quality:null,resolution};value.digest=U.sha256(value);return value;}const execution=Flow.execute(resolution.execution_request),status=execution.status==='PASS'?(resolution.status==='READY_DEGRADED'?'PASS_DEGRADED':'PASS'):execution.status,value={schema:ADAPTIVE_RESULT_SCHEMA,version:'1.0.0',status,candidate_ready:execution.candidate_ready===true,requested_quality:resolution.requested_quality,realized_quality:resolution.realized_quality,degraded:resolution.degraded===true,profile_id:resolution.profile_id,schedule:resolution.schedule,resolution_digest:resolution.digest,execution};value.digest=U.sha256({status:value.status,requested_quality:value.requested_quality,realized_quality:value.realized_quality,degraded:value.degraded,profile_id:value.profile_id,schedule_digest:value.schedule&&value.schedule.digest,resolution_digest:value.resolution_digest,execution_digest:execution.digest||execution.final_state_digest||execution.plan_digest});return value;}
function run(request){request=request||{};const mode=String(request.mode||'');if(mode==='adaptive-plan')return adaptivePlan(request);if(mode==='adaptive-execute')return adaptiveExecute(request);return Flow.run(request);}
module.exports=Object.freeze({
  version:'1.1.0',
  summary,
  catalog:Flow.catalog,
  discover:Flow.discover,
  compile:Flow.compile,
  execute:Flow.execute,
  adaptivePlan,
  adaptiveExecute,
  qualityProfiles:Quality.registry,
  run,
});
