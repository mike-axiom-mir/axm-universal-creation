'use strict';
const assert=require('assert');
const G=require('./creative-quality-gauntlet');
const Flow=require('./creative-flow');

const report=G.run();
assert.equal(report.schema,G.SCHEMA);
assert(report.public_hands>=501);
assert(report.callable_recipes>=508);
assert.equal(report.goal_only_status,'HOLD_PLAN_REQUIRED');
assert.deepEqual(report.levels.map((x)=>x.level),G.LEVELS);
assert(report.levels.every((x)=>x.status==='PASS'&&x.candidate_ready===true));
for(let i=1;i<report.levels.length;i++)assert(report.levels[i].steps>report.levels[i-1].steps);
assert(report.levels.find((x)=>x.level==='draft').families.includes('mesh-primitive'));
assert(report.levels.find((x)=>x.level==='game-ready').families.includes('mesh-topology'));
assert(report.levels.find((x)=>x.level==='production').families.includes('uv-production'));
assert(report.levels.find((x)=>x.level==='production').families.includes('material'));
const max=report.levels.find((x)=>x.level==='max-current-body');
for(const family of ['material-stack','rig-skeleton','rig-skin','animation-clip'])assert(max.families.includes(family));
assert(report.timings.every((x)=>Number.isFinite(x.elapsed_ms)&&x.elapsed_ms>=0));
assert.equal(report.gaps.length,6);

const deepest=Flow.run(G.build('max-current-body'));
assert.equal(deepest.status,'PASS');
assert.equal(deepest.final_state.finishedMaterial.schema,'axm.precision-material/v1');
assert.equal(deepest.final_state.packedUv.schema,'axm.precision-uv-layout/v1');
assert.equal(deepest.final_state.deformed.schema,'axm.precision-mesh/v1');
assert.equal(deepest.final_state.skinValidation.status,'PASS');
assert(deepest.final_state.baked.frames.length>1);
assert(deepest.final_state.animatedBounds.size.every((x)=>x>0));

console.log(JSON.stringify({status:'PASS',gauntlet:report},null,2));
