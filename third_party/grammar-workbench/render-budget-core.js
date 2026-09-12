(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.AXMGrammarGlassRenderBudgetCore=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const MODES=Object.freeze({SAFE:384,BALANCED:768,FULL:Infinity});
  const MODE_ORDER=Object.freeze(['SAFE','BALANCED','FULL']);

  function hash(value){
    let h=2166136261;
    const text=String(value??'');
    for(let i=0;i<text.length;i++){
      h^=text.charCodeAt(i);
      h=Math.imul(h,16777619);
    }
    return h>>>0;
  }

  function normalizeMode(mode,count){
    const requested=String(mode||'AUTO').toUpperCase();
    if(requested==='AUTO')return count>800?'SAFE':'FULL';
    return Object.hasOwn(MODES,requested)?requested:'SAFE';
  }

  function createPlan(atoms,{mode='AUTO'}={}){
    if(!Array.isArray(atoms))throw new Error('GRAMMAR_GLASS_RENDER_BUDGET_ATOMS_REQUIRED');
    const resolvedMode=normalizeMode(mode,atoms.length);
    const limit=Math.min(atoms.length,Number.isFinite(MODES[resolvedMode])?MODES[resolvedMode]:atoms.length);
    const entries=atoms.map((atom,index)=>({atom,index,rank:hash(`${atom?.languageId||''}|${atom?.atomType||''}|${atom?.atomId||index}`)}));
    let selected=entries;
    if(limit<entries.length){
      const groups=new Map();
      for(const entry of entries){
        const languageId=String(entry.atom?.languageId||'UNKNOWN');
        if(!groups.has(languageId))groups.set(languageId,[]);
        groups.get(languageId).push(entry);
      }
      const ordered=[...groups.entries()].sort(([a],[b])=>a.localeCompare(b));
      for(const [,items] of ordered)items.sort((a,b)=>a.rank-b.rank||a.index-b.index);
      selected=[];
      let depth=0;
      while(selected.length<limit){
        let added=false;
        for(const [,items] of ordered){
          if(items[depth]){
            selected.push(items[depth]);
            added=true;
            if(selected.length===limit)break;
          }
        }
        if(!added)break;
        depth++;
      }
      selected.sort((a,b)=>a.index-b.index);
    }
    const selectedAtomIds=selected.map(entry=>String(entry.atom?.atomId??entry.index));
    const core={
      schema:'axm.code.grammar-glass-render-budget.v1',
      version:'1.0.0',
      mode:resolvedMode,
      evidenceAtomCount:atoms.length,
      renderedAtomCount:selected.length,
      projectionHeldAtomCount:atoms.length-selected.length,
      languageCoverageCount:new Set(selected.map(entry=>entry.atom?.languageId)).size,
      entries:selected.map(({atom,index})=>({atom,index})),
      selectionFingerprint:hash(selectedAtomIds.join('|')).toString(16).padStart(8,'0'),
      truth:{
        fullEvidenceRetained:true,
        projectionBudgetCreatesEvidence:false,
        projectionBudgetRanksAtoms:false,
        omittedFromProjectionMeansAbsent:false,
        recordedStateMutation:false,
        authority:'NONE'
      }
    };
    return Object.freeze(core);
  }

  function nextMode(mode){
    const current=String(mode||'SAFE').toUpperCase();
    const index=MODE_ORDER.indexOf(current);
    return MODE_ORDER[(index<0?0:index+1)%MODE_ORDER.length];
  }

  return Object.freeze({MODES,MODE_ORDER,createPlan,nextMode,normalizeMode});
});
