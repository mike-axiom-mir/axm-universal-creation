(()=>{'use strict';
const root=typeof window!=='undefined'?window:globalThis;
const MODES=Object.freeze(['GRAVITY_WELL','RIFT_SCAN','DARK_MATTER','STAR_HUNT']);
function canon(v){if(v===null||typeof v!=='object')return JSON.stringify(v);if(Array.isArray(v))return`[${v.map(canon).join(',')}]`;return`{${Object.keys(v).sort().map(k=>`${JSON.stringify(k)}:${canon(v[k])}`).join(',')}}`}
function sha256(value){const text=typeof value==='string'?value:canon(value);if(typeof require==='function'){try{return require('crypto').createHash('sha256').update(text).digest('hex')}catch{}}if(root&&root.AXMInterglassExecutor&&typeof root.AXMInterglassExecutor.sha256==='function')return root.AXMInterglassExecutor.sha256(text);throw Error('PLAYGROUND_SHA256_ADAPTER_REQUIRED')}
function clamp(v,min,max){v=Number(v);return Number.isFinite(v)?Math.max(min,Math.min(max,v)):min}
function uniq(xs){return[...new Set((Array.isArray(xs)?xs:[]).map(v=>String(v||'').trim()).filter(Boolean))]}
function validSnapshot(s){return!!(s&&s.schema==='axm.code.grammar-glass-visual-snapshot.v1'&&s.cycle&&Array.isArray(s.cycle.atoms)&&Array.isArray(s.cycle.edges)&&Array.isArray(s.draftSky))}
function availableLanguages(snapshot){if(!validSnapshot(snapshot))throw Error('PLAYGROUND_VALID_GRAMMAR_GLASS_SNAPSHOT_REQUIRED');return uniq(snapshot.cycle.atoms.map(a=>a.languageId)).sort()}
function sourceBinding(snapshot){return Object.freeze({schema:snapshot.schema,version:snapshot.version||null,rootSeed:snapshot.rootSeed||null,sourceMode:snapshot.sourceMode||null,sourceSha256:snapshot.sourceSha256||null,profileSnapshotSha256:snapshot.profileSnapshotSha256||null,cycleSha256:snapshot.cycle.cycleSha256||null,conditionSha256:snapshot.cycle.conditionSha256||null})}
function rollLanguages(snapshot,{count=5,roll=0}={}){const langs=availableLanguages(snapshot),n=Math.max(1,Math.min(langs.length,Math.floor(Number(count)||5))),r=Math.max(0,Math.floor(Number(roll)||0)),seed=String(snapshot.rootSeed||snapshot.cycle.cycleSha256||'grammar-glass');return langs.map(languageId=>({languageId,score:sha256(`${seed}|PLAYGROUND_ROLL|${r}|${languageId}`)})).sort((a,b)=>a.score.localeCompare(b.score)||a.languageId.localeCompare(b.languageId)).slice(0,n).map(x=>x.languageId)}
function createProbe(snapshot,{languageIds=[],mode='GRAVITY_WELL',strength=.72,roll=0}={}){
 if(!validSnapshot(snapshot))throw Error('PLAYGROUND_VALID_GRAMMAR_GLASS_SNAPSHOT_REQUIRED');
 if(!MODES.includes(mode))throw Error(`PLAYGROUND_UNKNOWN_MODE:${mode}`);
 const available=new Set(availableLanguages(snapshot)),selected=uniq(languageIds).filter(id=>available.has(id)).slice(0,12);
 if(!selected.length)throw Error('PLAYGROUND_AT_LEAST_ONE_REAL_GRAMMAR_REQUIRED');
 const selectedSet=new Set(selected),atomById=new Map(snapshot.cycle.atoms.map(a=>[a.atomId,a]));
 const atoms=snapshot.cycle.atoms.filter(a=>selectedSet.has(a.languageId));
 const relationEdges=(snapshot.cycle.edges||[]).filter(e=>selectedSet.has(atomById.get(e.leftAtomId)?.languageId)&&selectedSet.has(atomById.get(e.rightAtomId)?.languageId));
 const directCarries=(snapshot.cycle.influenceCarries||[]).filter(e=>selectedSet.has(atomById.get(e.sourceAtomId)?.languageId)&&selectedSet.has(atomById.get(e.targetAtomId)?.languageId));
 const memoryPaths=(snapshot.contactMemory?.multiHopPaths||[]).filter(path=>{const hits=new Set((path.pathAtomIds||[]).map(id=>atomById.get(id)?.languageId).filter(id=>selectedSet.has(id)));return hits.size>=2});
 const draftStars=(snapshot.draftSky||[]).map(star=>{const overlap=uniq(star.languageIds||[]).filter(id=>selectedSet.has(id));return{star,overlap}}).filter(x=>x.overlap.length);
 const connectionClassCounts={};for(const edge of relationEdges){const key=String(edge.connectionClass||'UNKNOWN');connectionClassCounts[key]=(connectionClassCounts[key]||0)+1}
 const normalizedRoll=Math.max(0,Math.floor(Number(roll)||0)),binding=sourceBinding(snapshot);
 const combinationIdentitySha256=sha256({rootSeed:binding.rootSeed,cycleSha256:binding.cycleSha256,roll:normalizedRoll,languageIds:selected});
 const core={
  schema:'axm.code.grammar-glass-playground-probe.v1',version:'1.1.0',result:'VISUAL_GRAMMAR_PROBE_READY_NO_MUTATION',mode,
  strength:clamp(strength,0,1),roll:normalizedRoll,languageIds:selected,sourceBinding:binding,
  exploration:{result:'SEEDED_COMBINATION_SURFACED_FOR_INSPECTION',combinationIdentitySha256,replayInputs:{rootSeed:binding.rootSeed,cycleSha256:binding.cycleSha256,roll:normalizedRoll,languageIds:selected},unfamiliarityState:'UNASSESSED',codeCandidateState:'NOT_CONSTRUCTED'},
  metrics:{selectedGrammarCount:selected.length,selectedAtomCount:atoms.length,relationEdgeCount:relationEdges.length,directCarryCount:directCarries.length,crossGrammarDirectCarryCount:directCarries.filter(x=>x.crossGrammar).length,memoryPathCount:memoryPaths.length,draftStarCount:draftStars.length,connectionClassCounts},
  relationRefs:relationEdges.slice(0,96).map(e=>({leftAtomId:e.leftAtomId,rightAtomId:e.rightAtomId,connectionClass:e.connectionClass||null,thresholdMet:e.thresholdMet===true,crossGrammar:e.crossGrammar===true})),
  directCarryRefs:directCarries.slice(0,96).map(e=>({sourceAtomId:e.sourceAtomId,targetAtomId:e.targetAtomId,carryClass:e.carryClass||e.influenceCarryClass||null,signedDeltaPpm:Number(e.signedDeltaPpm||0),crossGrammar:e.crossGrammar===true,carrySha256:e.carrySha256||e.influenceCarrySha256||null})),
  memoryPathRefs:memoryPaths.slice(0,48).map(p=>({pathAtomIds:[...(p.pathAtomIds||[])],pathSha256:p.pathSha256||p.multiHopPathSha256||null,hopCount:p.hopCount||Math.max(0,(p.pathAtomIds||[]).length-1)})),
  draftStarRefs:draftStars.slice(0,48).map(({star,overlap})=>({starSha256:star.starSha256||star.draftStarSha256||null,cycleStep:star.cycleStep??null,languageIds:[...(star.languageIds||[])],selectedOverlap:overlap})),
  truth:{visualProbeOnly:true,visualSelectionCreatesEvidence:false,visualWarpCreatesEvidence:false,seededCombinationSearchPreserved:true,visualFrameCadenceChoosesCombinations:false,unfamiliarCombinationMayBecomeCandidate:true,unknownCombinationIsNotNoveltyProof:true,candidateRequiresExplicitConstructionAndVerification:true,cycleMutationPerformed:false,contactMemoryMutationPerformed:false,draftStarCreated:false,candidateCreated:false,executionRequested:false,automaticReentry:false,rankingPerformed:false,winnerSelected:false,semanticEquivalenceInferred:false,probeIsNotExecutableSoftware:true,probeIsNotNoveltyProof:true,sourceSnapshotRemainsAuthoritativeForRecordedEvidence:true,authority:'NONE'}
 };
 return Object.freeze({...core,probeSha256:sha256(core)});
}
const api=Object.freeze({MODES,canon,sha256,validSnapshot,availableLanguages,rollLanguages,createProbe});
if(typeof module!=='undefined'&&module.exports)module.exports=api;if(root)root.AXMGrammarGlassPlaygroundCore=api;
})();
