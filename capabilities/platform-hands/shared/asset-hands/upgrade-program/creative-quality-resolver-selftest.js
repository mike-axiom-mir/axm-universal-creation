'use strict';

const assert=require('assert');
const Resolver=require('./creative-quality-resolver');
const Profiles=require('./creative-quality-profiles');
const Service=require('../creative-flow-service');

const GOAL='Create a high quality animated armored sci-fi supply crate game asset with editable materials and animation.';
const registry=Profiles.registry();assert.equal(registry.profiles.length,1);assert.equal(registry.profiles[0].id,'game-prop.armored-crate/v1');
assert.equal(Profiles.normalizeQuality('draft'),.15);assert.equal(Profiles.normalizeQuality('high'),.85);assert.equal(Profiles.normalizeQuality('max'),1);assert.equal(Profiles.normalizeQuality(.73),.73);

const unknown=Resolver.resolve({goal:'paint a watercolor portrait of a lighthouse',quality:.8});assert.equal(unknown.status,'HOLD_UNSUPPORTED_GOAL');
const draft=Resolver.resolve({goal:GOAL,quality:.2});assert.equal(draft.status,'READY');assert.equal(draft.execution_request.steps.length,3);assert.equal(draft.realized_band,'draft');
const game=Resolver.resolve({goal:GOAL,quality:.45,machine:{concurrency:4}});assert.equal(game.status,'READY');assert.equal(game.execution_request.steps.length,18);assert.equal(game.realized_band,'game-ready');assert(game.schedule.groups.some((g)=>g.steps.length>1));assert(game.schedule.groups.every((g)=>g.steps.length<=4));
const production=Resolver.resolve({goal:GOAL,quality:.72});assert.equal(production.status,'READY');assert.equal(production.execution_request.steps.length,32);assert.equal(production.realized_band,'production');
const currentMax=Resolver.resolve({goal:GOAL,quality:.9});assert.equal(currentMax.status,'READY');assert.equal(currentMax.execution_request.steps.length,47);assert.equal(currentMax.realized_band,'max-current-body');assert(currentMax.estimate.serial_work_units>production.estimate.serial_work_units);assert(currentMax.estimate.state_bytes_estimate>production.estimate.state_bytes_estimate);

const maximum=Resolver.resolve({goal:GOAL,quality:'maximum'});assert.equal(maximum.status,'HOLD_CAPABILITY_GAP');assert(maximum.missing_capabilities.some((x)=>x.hand_id==='creative.mesh-model-finish.bevel'));assert.equal(maximum.gap_contract.schema,'axm.creative-capability-gap/v1');
const maximumAdaptive=Resolver.resolve({goal:GOAL,quality:'maximum',machine:{allow_quality_degrade:true}});assert.equal(maximumAdaptive.status,'READY_DEGRADED');assert(maximumAdaptive.realized_quality<.92&&maximumAdaptive.realized_quality>=.85);assert(maximumAdaptive.degradation_reasons.some((x)=>x.kind==='capability_gap'));

const hardBudget=Resolver.resolve({goal:GOAL,quality:.8,machine:{max_steps:20}});assert.equal(hardBudget.status,'HOLD_BUDGET');assert(hardBudget.budget_overages.some((x)=>x.kind==='steps'));
const adaptiveBudget=Resolver.resolve({goal:GOAL,quality:.8,machine:{max_steps:20,allow_quality_degrade:true}});assert.equal(adaptiveBudget.status,'READY_DEGRADED');assert(adaptiveBudget.execution_request.steps.length<=20);assert(adaptiveBudget.realized_quality<.6);
const noCalibration=Resolver.resolve({goal:GOAL,quality:.8,machine:{time_budget_ms:100}});assert.equal(noCalibration.status,'HOLD_CALIBRATION_REQUIRED');
const slow=Resolver.resolve({goal:GOAL,quality:.9,machine:{time_budget_ms:100,work_units_per_ms:.25,allow_quality_degrade:true}});assert(['READY','READY_DEGRADED'].includes(slow.status));const fast=Resolver.resolve({goal:GOAL,quality:.9,machine:{time_budget_ms:100,work_units_per_ms:2,allow_quality_degrade:true}});assert(['READY','READY_DEGRADED'].includes(fast.status));assert(fast.realized_quality>=slow.realized_quality);assert(fast.estimate.time_ms_estimate<=100+1e-9);

const plan=Service.run({mode:'adaptive-plan',goal:GOAL,quality:.9,machine:{concurrency:4}});assert.equal(plan.status,'READY');assert.equal(plan.execution_request.steps.length,47);assert.equal(plan.schedule.parallel_runtime,'PLANNED_NOT_EXECUTED');
const executed=Service.run({mode:'adaptive-execute',goal:GOAL,quality:.9,machine:{concurrency:4}});assert.equal(executed.status,'PASS');assert.equal(executed.requested_quality,.9);assert.equal(executed.realized_quality,.9);assert.equal(executed.execution.receipts.length,47);assert.equal(executed.execution.status,'PASS');assert.equal(executed.schedule.parallel_runtime,'PLANNED_NOT_EXECUTED');assert(executed.execution.final_state.finishedMaterial);assert(executed.execution.final_state.baked);assert(executed.execution.final_state.animatedBounds);
const degradedExecution=Service.run({mode:'adaptive-execute',goal:GOAL,quality:1,machine:{allow_quality_degrade:true,max_steps:64}});assert.equal(degradedExecution.status,'PASS_DEGRADED');assert(degradedExecution.realized_quality<1);assert.equal(degradedExecution.execution.status,'PASS');

console.log(JSON.stringify({status:'PASS',profiles:registry.profiles.length,quality:{draft:draft.realized_quality,game:game.realized_quality,production:production.realized_quality,current_max:currentMax.realized_quality,maximum_hold:maximum.status,maximum_adaptive:maximumAdaptive.realized_quality},budgets:{hard:hardBudget.status,adaptive:adaptiveBudget.realized_quality,slow:slow.realized_quality,fast:fast.realized_quality},schedule:{game_groups:game.schedule.group_count,current_groups:currentMax.schedule.group_count,serial_work:currentMax.schedule.serial_work_units,parallel_floor:currentMax.schedule.parallel_floor_work_units},adaptive_execution:{status:executed.status,steps:executed.execution.receipts.length,degraded_status:degradedExecution.status}},null,2));
