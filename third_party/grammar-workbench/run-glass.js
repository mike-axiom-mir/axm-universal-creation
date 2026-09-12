'use strict';
const fs=require('node:fs');
try {
 const raw=fs.readFileSync(0); if(raw.length>1048576)throw Error('INPUT_TOO_LARGE');
 const x=JSON.parse(raw.toString('utf8'));let result;
 if(process.argv[2]==='render-budget'){
  if(!Array.isArray(x.atoms)||x.atoms.length>10000)throw Error('ATOMS_REQUIRE_0_TO_10000');
  if(x.mode&&!['AUTO','SAFE','BALANCED','FULL'].includes(x.mode))throw Error('UNKNOWN_MODE');
  result=require('./render-budget-core.js').createPlan(x.atoms,{mode:x.mode});
 }else if(process.argv[2]==='state-ripple'){
  const r=require('./state-ripple-core.js');
  const f=r.createFabric(x.fabric);const base=r.runAll(f,x.initialState);
  if(!base.baseline)result=base;
  else result=r.shadowVerify(f,x.changedState,base.baseline,{wakeBudget:x.wakeBudget??4096});
 }else throw Error('UNKNOWN_OPERATION');
 process.stdout.write(JSON.stringify(result));
}catch(e){process.stderr.write(JSON.stringify({error:e.message}));process.exitCode=2;}
