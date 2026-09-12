'use strict';
const assert=require('assert');
const Ripple=require('./state-ripple-core.js');
const Program=require('./construction-program-core.js');
let assertions=0;
function ok(v,m){assert.ok(v,m);assertions++;}
function eq(a,b,m){assert.deepStrictEqual(a,b,m);assertions++;}
function throws(fn,part){assert.throws(fn,e=>String(e.message||e).includes(part));assertions++;}

function buildLargeFabric({opaqueNodeIds=[]}={}){
  const nodes=[];
  const finals=[];
  for(let c=0;c<100;c++){
    const cc=String(c).padStart(3,'0');
    for(let n=0;n<10;n++){
      const nn=String(n).padStart(2,'0');
      const id=`c${cc}-n${nn}`;
      const source=n===0?`inputs.c${cc}`:`work.c${cc}.v${String(n-1).padStart(2,'0')}`;
      const target=`work.c${cc}.v${nn}`;
      nodes.push({id,reads:[source],writes:[target],dependsOn:[],effects:[],operations:[{op:'COPY',from:source,path:target}]});
    }
    finals.push(`work.c${cc}.v09`);
  }
  nodes.push({id:'zz-aggregate',reads:finals,writes:['summary.total'],dependsOn:[],effects:[],operations:[{op:'SUM',paths:finals,path:'summary.total'}]});
  return Ripple.createFabric({fabricId:'stress-100x10',nodes,opaqueNodeIds});
}
function input(values={}){const inputs={};for(let c=0;c<100;c++){const cc=String(c).padStart(3,'0');inputs[`c${cc}`]=values[cc]||0;}return{inputs};}

const fabric=buildLargeFabric();
ok(Ripple.validFabric(fabric),'large fabric valid');
eq(fabric.nodeCount,1001);
const baseRun=Ripple.runAll(fabric,input());
eq(baseRun.result,'STATE_RIPPLE_FULL_RUN_COMPLETE');
eq(baseRun.executedNodeCount,1001);
eq(baseRun.finalState.summary.total,0);
ok(Ripple.validBaseline(fabric,baseRun.baseline));

const changed=input({'042':7});
const sparse=Ripple.sparseUpdate(fabric,changed,baseRun.baseline,{wakeBudget:20});
eq(sparse.result,'STATE_RIPPLE_SPARSE_UPDATE_COMPLETE');
eq(sparse.executedNodeCount,11);
eq(sparse.reusedNodeCount,990);
eq(sparse.conservativeWakeNodeCount,11);
eq(sparse.finalState.summary.total,7);
ok(sparse.reuseFraction>0.98);
ok(baseRun.baseline.cache['c000-n00']===sparse.nextBaseline.cache['c000-n00'],'retained cache object identity');
ok(baseRun.baseline.cache['c042-n00']!==sparse.nextBaseline.cache['c042-n00'],'changed cache rebuilt');

const shadow=Ripple.shadowVerify(fabric,changed,baseRun.baseline,{wakeBudget:20});
eq(shadow.result,'STATE_RIPPLE_SPARSE_FULL_EQUIVALENCE_PASS');
ok(shadow.finalStateEquivalent);ok(shadow.nodeOutputsEquivalent);ok(shadow.effectsEquivalent);
eq(shadow.fullExecutedNodeCount,1001);eq(shadow.sparseExecutedNodeCount,11);

const held=Ripple.sparseUpdate(fabric,changed,baseRun.baseline,{wakeBudget:5});
eq(held.result,'STATE_RIPPLE_HELD_GLOBAL_WAKE_BUDGET');
eq(held.executedNodeCount,0);eq(held.finalState,null);eq(held.nextBaseline,null);

const noChange=Ripple.sparseUpdate(fabric,input(),baseRun.baseline,{wakeBudget:0});
eq(noChange.result,'STATE_RIPPLE_SPARSE_UPDATE_COMPLETE');
eq(noChange.executedNodeCount,0);eq(noChange.reusedNodeCount,1001);eq(noChange.conservativeWakeNodeCount,0);

const opaqueFabric=buildLargeFabric({opaqueNodeIds:['c000-n00']});
const opaqueBase=Ripple.runAll(opaqueFabric,input());
const opaque=Ripple.sparseUpdate(opaqueFabric,input(),opaqueBase.baseline,{wakeBudget:20});
eq(opaque.result,'STATE_RIPPLE_SPARSE_UPDATE_COMPLETE');
eq(opaque.conservativeWakeNodeCount,11);eq(opaque.executedNodeCount,1);eq(opaque.reusedNodeCount,1000);
ok(opaqueBase.baseline.cache['c000-n00']!==opaque.nextBaseline.cache['c000-n00']);
ok(opaqueBase.baseline.cache['c000-n01']===opaque.nextBaseline.cache['c000-n01']);
const opaqueShadow=Ripple.shadowVerify(opaqueFabric,input(),opaqueBase.baseline,{wakeBudget:20});eq(opaqueShadow.result,'STATE_RIPPLE_SPARSE_FULL_EQUIVALENCE_PASS');

throws(()=>Ripple.createFabric({nodes:[{id:'a',reads:[],writes:['x'],dependsOn:[],effects:[],operations:[{op:'COPY',from:'input.x',path:'x'}]}]}),'UNDECLARED_READ');
throws(()=>Ripple.createFabric({nodes:[{id:'a',reads:[],writes:['x'],dependsOn:[],effects:[],operations:[{op:'SET',path:'x',value:1}]},{id:'b',reads:[],writes:['x'],dependsOn:[],effects:[],operations:[{op:'SET',path:'x',value:2}]}]}),'AMBIGUOUS_WRITE_ORDER');
throws(()=>Ripple.createFabric({nodes:[{id:'a',reads:[],writes:['a'],dependsOn:['b'],effects:[],operations:[{op:'SET',path:'a',value:1}]},{id:'b',reads:[],writes:['b'],dependsOn:['a'],effects:[],operations:[{op:'SET',path:'b',value:1}]}]}),'DEPENDENCY_CYCLE');

const program=Program.createProgram({programId:'fixture',binding:{preparationSha256:'prep'},modules:[{id:'a',reads:[],writes:['out.x'],dependsOn:[],effects:[],operations:[{op:'SET',path:'out.x',value:7}]}]});
const adapted=Ripple.fromConstructionProgram(program);
eq(adapted.binding.constructionProgramSha256,program.programSha256);eq(adapted.nodeCount,1);

const other=Ripple.createFabric({fabricId:'other',nodes:[{id:'x',reads:['input.x'],writes:['out.x'],dependsOn:[],effects:[],operations:[{op:'COPY',from:'input.x',path:'out.x'}]}]});
throws(()=>Ripple.sparseUpdate(other,{input:{x:1}},baseRun.baseline,{wakeBudget:10}),'CURRENT_BASELINE_REQUIRED');

let rollingBaseline=baseRun.baseline;
let values={};
let totalSparseExec=0;
for(let i=0;i<64;i++){
  const cc=String((i*37)%100).padStart(3,'0'); values={...values,[cc]:(values[cc]||0)+1};
  const state=input(values);
  const proof=Ripple.shadowVerify(fabric,state,rollingBaseline,{wakeBudget:20});
  eq(proof.result,'STATE_RIPPLE_SPARSE_FULL_EQUIVALENCE_PASS');
  ok(proof.sparse.executedNodeCount<=11);
  totalSparseExec+=proof.sparse.executedNodeCount;
  rollingBaseline=proof.sparse.nextBaseline;
}
ok(totalSparseExec<=64*11);

console.log(JSON.stringify({result:'GRAMMAR_GLASS_STATE_RIPPLE_SELFTEST_PASS',assertions,nodeCount:fabric.nodeCount,baselineFullExecutions:baseRun.executedNodeCount,singleMutationSparseExecutions:sparse.executedNodeCount,singleMutationReused:sparse.reusedNodeCount,reusePercent:Number((sparse.reuseFraction*100).toFixed(3)),stressUpdates:64,stressSparseExecutions:totalSparseExec,authority:'NONE'},null,2));
