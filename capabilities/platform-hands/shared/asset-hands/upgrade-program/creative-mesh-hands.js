'use strict';
const U=require('./foundation-utils');const Mesh=require('./precision-mesh');
const HAND_SCHEMA='axm.creative-executable-hand/v1',RESULT_SCHEMA='axm.creative-executable-hand-result/v1';
const PRIMITIVES=['cube','sphere','cylinder','cone','plane','torus'];
const TRANSFORMS=['translate','scale','rotate-x','rotate-y','rotate-z','mirror-x','mirror-y','mirror-z'];
const DEFORMS=['inflate','twist','taper','bend','flatten-x','flatten-y','flatten-z','noise-displace'];
const TOPOLOGY=['recalc-normals','flip-winding','center-origin','normalize-scale','remove-degenerate','compact','weld','merge','subdivide'];
const UV=['planar-x','planar-y','planar-z','spherical','cylindrical','normalize'];
const ANALYSIS=['bounds','surface-area','volume','centroid','topology'];
function title(id){return id.split('-').map((v)=>v.charAt(0).toUpperCase()+v.slice(1)).join(' ');}function descriptor(family,operation,outputs){const value={schema:HAND_SCHEMA,version:'1.0.1',id:'creative.'+family+'.'+operation,title:title(operation),family,operation,state:'EXECUTABLE',deterministic:true,outputs:outputs||['axm.precision-mesh/v1'],truth:'UC-native deterministic precision-mesh operation built on existing Spatial Studio geometry where applicable; no DCC product code or UI is embedded.'};value.digest=U.sha256(value);return Object.freeze(value);}
const DESCRIPTORS=Object.freeze([...PRIMITIVES.map((op)=>descriptor('mesh-primitive',op)),...TRANSFORMS.map((op)=>descriptor('mesh-transform',op)),...DEFORMS.map((op)=>descriptor('mesh-deform',op)),...TOPOLOGY.map((op)=>descriptor('mesh-topology',op)),...UV.map((op)=>descriptor('mesh-uv',op)),...ANALYSIS.map((op)=>descriptor('mesh-analysis',op,['application/json']))]);
const BY_ID=new Map(DESCRIPTORS.map((d)=>[d.id,d]));function list(){return DESCRIPTORS.map((d)=>JSON.parse(JSON.stringify(d)));}function get(id){const d=BY_ID.get(String(id||''));return d?JSON.parse(JSON.stringify(d)):null;}function wrap(hand,result){const value={schema:RESULT_SCHEMA,version:'1.0.1',status:'EXECUTED',hand_id:hand.id,hand_digest:hand.digest,result};value.digest=U.sha256(value);return value;}
function invoke(id,args){const hand=BY_ID.get(String(id||''));U.ensure(hand,'unknown creative mesh hand: '+id);args=args||{};let result;
  if(hand.family==='mesh-primitive')result=Mesh.primitive(hand.operation,args.spec||args);
  else if(hand.family==='mesh-transform'){
    if(hand.operation==='translate')result=Mesh.translate(args.mesh,args.vector);
    else if(hand.operation==='scale'){const v=args.vector==null?args.factor:args.vector,values=typeof v==='number'?[v,v,v]:Array.from(v||[]);U.ensure(values.length===3&&values.every((x)=>Number.isFinite(Number(x))&&Number(x)>0),'mesh scale hand requires positive components; use explicit mirror hands for reflection');result=Mesh.scale(args.mesh,values.map(Number));}
    else if(hand.operation.startsWith('rotate-'))result=Mesh.rotate(args.mesh,hand.operation.slice(-1),args.degrees);
    else result=Mesh.mirror(args.mesh,hand.operation.slice(-1));
  } else if(hand.family==='mesh-deform'){
    if(hand.operation==='inflate')result=Mesh.inflate(args.mesh,args.amount);
    else if(hand.operation==='twist')result=Mesh.twist(args.mesh,args.degrees);
    else if(hand.operation==='taper')result=Mesh.taper(args.mesh,args.factor);
    else if(hand.operation==='bend')result=Mesh.bend(args.mesh,args.degrees);
    else if(hand.operation.startsWith('flatten-'))result=Mesh.flatten(args.mesh,hand.operation.slice(-1),args.value);
    else result=Mesh.noiseDisplace(args.mesh,args.spec||args);
  } else if(hand.family==='mesh-topology'){
    if(hand.operation==='recalc-normals')result=Mesh.recalcNormals(args.mesh);
    else if(hand.operation==='flip-winding')result=Mesh.flipWinding(args.mesh);
    else if(hand.operation==='center-origin')result=Mesh.centerOrigin(args.mesh);
    else if(hand.operation==='normalize-scale')result=Mesh.normalizeScale(args.mesh,args.target);
    else if(hand.operation==='remove-degenerate')result=Mesh.removeDegenerate(args.mesh,args.epsilon);
    else if(hand.operation==='compact')result=Mesh.compact(args.mesh);
    else if(hand.operation==='weld')result=Mesh.weld(args.mesh,args.epsilon);
    else if(hand.operation==='merge')result=Mesh.merge(args.meshes,args.id);
    else if(hand.operation==='subdivide')result=Mesh.subdivide(args.mesh);
  } else if(hand.family==='mesh-uv'){
    if(hand.operation.startsWith('planar-'))result=Mesh.planarUv(args.mesh,hand.operation.slice(-1));
    else if(hand.operation==='spherical')result=Mesh.sphericalUv(args.mesh);
    else if(hand.operation==='cylindrical')result=Mesh.cylindricalUv(args.mesh);
    else result=Mesh.normalizeUv(args.mesh);
  } else if(hand.family==='mesh-analysis'){
    const map={'surface-area':'surfaceArea','volume':'signedVolume'};result=Mesh[map[hand.operation]||hand.operation](args.mesh);
  }
  U.ensure(result!=null,'mesh hand has no execution path: '+hand.id);return wrap(hand,result);
}
function audit(){const by_family={};for(const d of DESCRIPTORS)by_family[d.family]=(by_family[d.family]||0)+1;const value={schema:'axm.creative-mesh-hand-audit/v1',version:'1.0.1',total:DESCRIPTORS.length,counts:{EXECUTABLE:DESCRIPTORS.length},by_family,ids:DESCRIPTORS.map((d)=>d.id)};value.digest=U.sha256(value);return value;}
module.exports={HAND_SCHEMA,RESULT_SCHEMA,PRIMITIVES,TRANSFORMS,DEFORMS,TOPOLOGY,UV,ANALYSIS,list,get,invoke,audit};