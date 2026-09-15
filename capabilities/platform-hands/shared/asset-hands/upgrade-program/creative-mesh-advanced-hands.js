'use strict';
const U=require('./foundation-utils');
const Sculpt=require('./precision-mesh-sculpt');
const UV=require('./precision-mesh-uv-edit');
const Topology=require('./precision-mesh-topology-inspect');
const Mod=require('./precision-mesh-modifiers');
const HAND_SCHEMA='axm.creative-executable-hand/v1',RESULT_SCHEMA='axm.creative-executable-hand-result/v1';
const SCULPT=['grab','inflate','deflate','smooth','pinch','flatten','twist','noise'];
const UV_EDIT=['translate','scale','rotate','flip-u','flip-v','wrap','clamp','normalize-selected','planar-x','planar-y','planar-z'];
const TOPOLOGY=['boundary-loops','connected-components','face-neighbors','vertex-neighbors','edge-incidence','manifold-audit','degenerate-audit','euler','orientation-audit'];
const MODIFIERS=['solidify','array-linear','array-radial','snap-grid','snap-plane','shear','fit-bounds'];
function title(v){return v.split('-').map((x)=>x.charAt(0).toUpperCase()+x.slice(1)).join(' ');}function descriptor(family,operation,outputs){const d={schema:HAND_SCHEMA,version:'1.0.0',id:'creative.'+family+'.'+operation,title:title(operation),family,operation,state:'EXECUTABLE',deterministic:true,outputs:outputs||['application/json'],truth:'Deterministic UC precision-mesh operation over bounded local state; no external DCC implementation or UI is embedded.'};d.digest=U.sha256(d);return Object.freeze(d);}
const DESCRIPTORS=Object.freeze([...SCULPT.map((x)=>descriptor('mesh-sculpt',x)),...UV_EDIT.map((x)=>descriptor('mesh-uv-edit',x,['axm.precision-mesh/v1'])),...TOPOLOGY.map((x)=>descriptor('mesh-topology-inspect',x)),...MODIFIERS.map((x)=>descriptor('mesh-modifier',x,['axm.precision-mesh/v1']))]);
const BY_ID=new Map(DESCRIPTORS.map((d)=>[d.id,d]));
function list(){return DESCRIPTORS.map((d)=>JSON.parse(JSON.stringify(d)));}function get(id){const d=BY_ID.get(String(id||''));return d?JSON.parse(JSON.stringify(d)):null;}function wrap(hand,result){const v={schema:RESULT_SCHEMA,version:'1.0.0',status:'EXECUTED',hand_id:hand.id,hand_digest:hand.digest,result};v.digest=U.sha256(v);return v;}
function invoke(id,args){const hand=BY_ID.get(String(id||''));U.ensure(hand,'unknown advanced mesh hand: '+id);args=args||{};let r;
  if(hand.family==='mesh-sculpt')r=Sculpt[hand.operation](args.mesh,args.spec||args);
  else if(hand.family==='mesh-uv-edit'){
    const map={'flip-u':'flipU','flip-v':'flipV','normalize-selected':'normalizeSelected','planar-x':'planarX','planar-y':'planarY','planar-z':'planarZ'};
    const fn=UV[map[hand.operation]||hand.operation];
    if(['flip-u','flip-v','wrap','clamp','normalize-selected','planar-x','planar-y','planar-z'].includes(hand.operation))r=fn(args.mesh,args.selection);
    else r=fn(args.mesh,args.selection,args.spec||{});
  } else if(hand.family==='mesh-topology-inspect'){
    const map={'boundary-loops':'boundaryLoops','connected-components':'connectedComponents','face-neighbors':'faceNeighbors','vertex-neighbors':'vertexNeighbors','edge-incidence':'edgeIncidence','manifold-audit':'manifoldAudit','degenerate-audit':'degenerateAudit','orientation-audit':'orientationAudit'};
    const fn=Topology[map[hand.operation]||hand.operation];
    r=['face-neighbors','vertex-neighbors','degenerate-audit'].includes(hand.operation)?fn(args.mesh,args.spec||{}):fn(args.mesh);
  } else if(hand.family==='mesh-modifier'){
    const map={'array-linear':'arrayLinear','array-radial':'arrayRadial','snap-grid':'snapGrid','snap-plane':'snapPlane','fit-bounds':'fitBounds'};
    r=Mod[map[hand.operation]||hand.operation](args.mesh,args.spec||{});
  }
  U.ensure(r!=null,'advanced mesh hand has no execution path: '+hand.id);return wrap(hand,r);
}
function audit(){const by_family={};for(const d of DESCRIPTORS)by_family[d.family]=(by_family[d.family]||0)+1;const v={schema:'axm.creative-mesh-advanced-hand-audit/v1',version:'1.0.0',total:DESCRIPTORS.length,counts:{EXECUTABLE:DESCRIPTORS.length},by_family,ids:DESCRIPTORS.map((d)=>d.id)};v.digest=U.sha256(v);return v;}
module.exports={HAND_SCHEMA,RESULT_SCHEMA,SCULPT,UV_EDIT,TOPOLOGY,MODIFIERS,list,get,invoke,audit};