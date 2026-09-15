'use strict';

const U=require('./foundation-utils');
const CreativeHands=require('../creative-hands-service');
const Profiles=require('./creative-quality-profiles');

const RESOLUTION_SCHEMA='axm.creative-quality-resolution/v1';
const SCHEDULE_SCHEMA='axm.creative-quality-schedule/v1';
const GAP_SCHEMA='axm.creative-capability-gap/v1';
const DEFAULT_MAX_STATE_BYTES=64*1024*1024;
const MAX_CONCURRENCY=32;
const FAMILY_WORK=Object.freeze({
  'mesh-primitive':2,'mesh-transform':1,'mesh-topology':2,'mesh-analysis':1,
  'mesh-model-finish':6,'uv-production':4,procedural:2,material:3,'texture-projection':5,
  'material-stack':3,'material-generator':3,'rig-skeleton':2,'rig-skin':4,'animation-clip':3,
});

function finiteInt(value,label,min,max){const n=Math.floor(U.finite(value,label));U.ensure(n>=min&&n<=max,label+' outside '+min+'..'+max);return n;}
function normalizeMachine(input){
 input=U.clone(input||{});const machine={
  max_steps:input.max_steps==null?128:finiteInt(input.max_steps,'machine max_steps',1,128),
  max_work_units:input.max_work_units==null?1000000:finiteInt(input.max_work_units,'machine max_work_units',1,1000000000),
  max_state_bytes:input.max_state_bytes==null?DEFAULT_MAX_STATE_BYTES:finiteInt(input.max_state_bytes,'machine max_state_bytes',1024,1024*1024*1024),
  concurrency:input.concurrency==null?1:finiteInt(input.concurrency,'machine concurrency',1,MAX_CONCURRENCY),
  time_budget_ms:input.time_budget_ms==null?null:U.finite(input.time_budget_ms,'machine time_budget_ms'),
  work_units_per_ms:input.work_units_per_ms==null?null:U.finite(input.work_units_per_ms,'machine work_units_per_ms'),
  allow_quality_degrade:input.allow_quality_degrade===true,
 };
 if(input.allow_quality_degrade!=null)U.ensure(typeof input.allow_quality_degrade==='boolean','allow_quality_degrade must be boolean');
 if(machine.time_budget_ms!=null)U.ensure(machine.time_budget_ms>0&&machine.time_budget_ms<=3600000,'machine time_budget_ms outside 0..3600000');
 if(machine.work_units_per_ms!=null)U.ensure(machine.work_units_per_ms>0&&machine.work_units_per_ms<=1000000,'machine work_units_per_ms outside 0..1000000');
 machine.parallel_runtime='PLANNED_NOT_EXECUTED';
 machine.execution_budget_policy='serial Creative Flow execution remains authoritative in Wave 13; concurrency schedule is inspectable planning evidence only';
 return machine;
}
function collectStateRefs(value,out){out=out||[];if(Array.isArray(value)){for(const row of value)collectStateRefs(row,out);return out;}if(!value||typeof value!=='object')return out;if(Object.keys(value).length===1&&typeof value.$state==='string'){out.push(String(value.$state).split('.')[0]);return out;}for(const child of Object.values(value))collectStateRefs(child,out);return out;}
function inferFamily(id){if(String(id).includes('mesh-model-finish'))return'mesh-model-finish';return'unknown';}
function pixelWork(args){const spec=args&&args.spec||{},w=Number(spec.width||0),h=Number(spec.height||0);return Number.isFinite(w)&&Number.isFinite(h)&&w>0&&h>0?Math.ceil(w*h/4096):0;}
function stepWork(step){const hand=CreativeHands.get(step.hand_id),family=hand?hand.family:inferFamily(step.hand_id);let units=FAMILY_WORK[family]||2;if(['procedural','texture-projection'].includes(family))units+=pixelWork(step.args);if(family==='animation-clip'&&String(step.hand_id).endsWith('.bake-poses')){const fps=Number(step.args&&step.args.spec&&step.args.spec.fps||0);if(Number.isFinite(fps)&&fps>0)units+=Math.ceil(fps/8);}return Math.max(1,Math.ceil(units));}
function schedule(steps,concurrency,initialState){
 const producers=new Map(),byId=new Map(),costs=new Map();for(const s of steps){U.ensure(!byId.has(s.id),'duplicate quality step id: '+s.id);byId.set(s.id,s);costs.set(s.id,stepWork(s));if(s.save_as)producers.set(s.save_as,s.id);}const initial=new Set(Object.keys(initialState||{})),deps=new Map();for(const s of steps){const d=new Set((s.depends_on||[]).map(String));for(const name of collectStateRefs(s.args||{})){if(initial.has(name))continue;if(producers.has(name)&&producers.get(name)!==s.id)d.add(producers.get(name));}deps.set(s.id,Array.from(d).sort());}
 const done=new Set(),pending=new Set(steps.map((s)=>s.id)),groups=[];let parallelFloor=0;while(pending.size){const ready=Array.from(pending).filter((id)=>(deps.get(id)||[]).every((d)=>done.has(d))).sort();U.ensure(ready.length,'quality schedule contains unresolved dependency cycle');for(let i=0;i<ready.length;i+=concurrency){const ids=ready.slice(i,i+concurrency),serial=ids.reduce((sum,id)=>sum+costs.get(id),0),parallel=Math.max(...ids.map((id)=>costs.get(id)));groups.push({index:groups.length,steps:ids,serial_work_units:serial,parallel_floor_work_units:parallel});parallelFloor+=parallel;}for(const id of ready){pending.delete(id);done.add(id);}}
 const serialWork=Array.from(costs.values()).reduce((a,b)=>a+b,0),value={schema:SCHEDULE_SCHEMA,version:'1.0.0',concurrency,groups,group_count:groups.length,serial_work_units:serialWork,parallel_floor_work_units:parallelFloor,parallel_runtime:'PLANNED_NOT_EXECUTED'};value.digest=U.sha256(value);return value;
}
function missingHands(steps){const seen=new Set(),rows=[];for(const s of steps){if(CreativeHands.get(s.hand_id)||seen.has(s.hand_id))continue;seen.add(s.hand_id);rows.push({hand_id:s.hand_id,required_by_step:s.id,reason:'quality profile requires an executable hand that is absent from the current public Creative Hands catalog'});}return rows;}
function gapContract(profile,q,missing){if(!missing.length)return null;const value={schema:GAP_SCHEMA,version:'1.0.0',profile_id:profile.id,requested_quality:q,missing,forge_handoff:'EXPLICIT_GAP_READY',truth:'This is a scoped missing-operation contract. It does not claim the capability is impossible or absent from every lower-level UC subsystem.'};value.digest=U.sha256(value);return value;}
function effectiveWorkCap(machine){if(machine.time_budget_ms==null)return{cap:machine.max_work_units,calibration_required:false,time_cap:null};if(machine.work_units_per_ms==null)return{cap:machine.max_work_units,calibration_required:true,time_cap:null};const timeCap=Math.max(1,Math.floor(machine.time_budget_ms*machine.work_units_per_ms));return{cap:Math.min(machine.max_work_units,timeCap),calibration_required:false,time_cap:timeCap};}
function assess(profile,q,machine,state){
 const steps=profile.build(q),missing=missingHands(steps),sched=schedule(steps,machine.concurrency,state),stateBytes=profile.estimateStateBytes(q),cap=effectiveWorkCap(machine),overages=[];
 if(steps.length>machine.max_steps)overages.push({kind:'steps',required:steps.length,available:machine.max_steps});
 if(sched.serial_work_units>cap.cap)overages.push({kind:'work_units',required:sched.serial_work_units,available:cap.cap});
 if(stateBytes>machine.max_state_bytes)overages.push({kind:'state_bytes_estimate',required:stateBytes,available:machine.max_state_bytes});
 if(cap.calibration_required)overages.push({kind:'throughput_calibration',required:'work_units_per_ms',available:null});
 const estimate={steps:steps.length,serial_work_units:sched.serial_work_units,parallel_floor_work_units:sched.parallel_floor_work_units,state_bytes_estimate:stateBytes,time_ms_estimate:machine.work_units_per_ms==null?null:Math.round((sched.serial_work_units/machine.work_units_per_ms)*1000)/1000,parallel_time_floor_ms_estimate:machine.work_units_per_ms==null?null:Math.round((sched.parallel_floor_work_units/machine.work_units_per_ms)*1000)/1000};
 return{quality:q,steps,missing,schedule:sched,estimate,overages,fit:missing.length===0&&overages.length===0,gap_contract:gapContract(profile,q,missing)};
}
function degradationReasons(assessment){const rows=[];for(const m of assessment.missing)rows.push({kind:'capability_gap',hand_id:m.hand_id});for(const o of assessment.overages)rows.push({kind:'resource_limit',resource:o.kind,required:o.required,available:o.available});return rows;}
function findDegraded(profile,requested,machine,state){const start=Math.floor(requested*100-1e-9);for(let i=start;i>=0;i--){const q=i/100,a=assess(profile,q,machine,state);if(a.fit)return a;}return null;}
function qualityBand(q){if(q<.3)return'draft';if(q<.6)return'game-ready';if(q<.85)return'production';if(q<.92)return'max-current-body';return'premium';}
function resolve(request){
 request=U.clone(request||{});const goal=U.text(request.goal||'',2000,'adaptive quality goal'),requested=Profiles.normalizeQuality(request.quality),machine=normalizeMachine(request.machine),selected=Profiles.resolve(goal,request.profile_id),catalog=CreativeHands.audit();if(selected.status!=='MATCH'){const value={schema:RESOLUTION_SCHEMA,version:'1.0.0',status:selected.status,goal,requested_quality:requested,profile_id:request.profile_id||null,profile_candidates:selected.candidates||[],machine,hand_audit_digest:catalog.digest,truth:'No adaptive execution plan was invented because the deterministic quality profile registry could not resolve this goal uniquely.'};value.digest=U.sha256(value);return value;}
 const profile=selected.profile,state=request.state&&typeof request.state==='object'&&!Array.isArray(request.state)?request.state:{},initial=assess(profile,requested,machine,state);let chosen=initial,status='READY';if(!initial.fit&&machine.allow_quality_degrade){const degraded=findDegraded(profile,requested,machine,state);if(degraded){chosen=degraded;status='READY_DEGRADED';}}
 if(!chosen.fit){let hold='HOLD_BUDGET';if(chosen.missing.length)hold='HOLD_CAPABILITY_GAP';else if(chosen.overages.some((x)=>x.kind==='throughput_calibration'))hold='HOLD_CALIBRATION_REQUIRED';const value={schema:RESOLUTION_SCHEMA,version:'1.0.0',status:hold,goal,profile_id:profile.id,profile_score:selected.score,requested_quality:requested,requested_band:qualityBand(requested),realized_quality:null,machine,estimate:chosen.estimate,schedule:chosen.schedule,missing_capabilities:chosen.missing,budget_overages:chosen.overages,gap_contract:chosen.gap_contract,hand_audit_digest:catalog.digest,truth:'The requested quality was not silently relabeled as achieved.'};value.digest=U.sha256(value);return value;}
 const executionRequest={mode:'execute',goal,state,steps:chosen.steps};if(request.expose&&typeof request.expose==='object')executionRequest.expose=request.expose;const value={schema:RESOLUTION_SCHEMA,version:'1.0.0',status,goal,profile_id:profile.id,profile_score:selected.score,requested_quality:requested,requested_band:qualityBand(requested),realized_quality:chosen.quality,realized_band:qualityBand(chosen.quality),degraded:chosen.quality+1e-12<requested,degradation_reasons:chosen.quality+1e-12<requested?degradationReasons(initial):[],machine,estimate:chosen.estimate,schedule:chosen.schedule,missing_capabilities:[],budget_overages:[],gap_contract:initial.gap_contract,hand_audit_digest:catalog.digest,execution_request:executionRequest,truth:'Quality is a requested realization depth over one canonical creation route; resource adaptation may reduce expression depth but does not rewrite the caller goal or claim the requested quality was reached.'};value.digest=U.sha256(value);return value;
}
function registry(){return Profiles.registry();}
module.exports={RESOLUTION_SCHEMA,SCHEDULE_SCHEMA,GAP_SCHEMA,normalizeMachine,qualityBand,schedule,assess,resolve,registry};
