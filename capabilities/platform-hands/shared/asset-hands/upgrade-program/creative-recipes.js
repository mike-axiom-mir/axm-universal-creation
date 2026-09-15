'use strict';

const U=require('./foundation-utils');
const P=require('./creative-precision');
const R=require('./precision-raster');
const T=require('./precision-transform');
const Hands=require('./creative-hands');

const RECIPE_SCHEMA='axm.creative-tool-recipe/v1';
const REGISTRY_SCHEMA='axm.creative-tool-recipe-registry/v1';
const definitions={
  'selection.rectangle':{state:'EXECUTABLE',primitives:['mask.shape.rectangle']},
  'selection.ellipse':{state:'EXECUTABLE',primitives:['mask.shape.ellipse']},
  'selection.polygon':{state:'EXECUTABLE',primitives:['mask.shape.polygon']},
  'selection.magic-wand':{state:'EXECUTABLE',primitives:['raster.contiguous-colour-mask']},
  'selection.colour-range':{state:'EXECUTABLE',primitives:['raster.colour-range-mask']},
  'selection.luminance':{state:'EXECUTABLE',primitives:['raster.luminance-range-mask']},
  'selection.channel':{state:'EXECUTABLE',primitives:['raster.channel-mask']},
  'selection.edge':{state:'EXECUTABLE',primitives:['raster.sobel-edge-mask']},
  'selection.union':{state:'EXECUTABLE',primitives:['mask.combine.union']},
  'selection.intersection':{state:'EXECUTABLE',primitives:['mask.combine.intersection']},
  'selection.subtract':{state:'EXECUTABLE',primitives:['mask.combine.subtract']},
  'selection.xor':{state:'EXECUTABLE',primitives:['mask.combine.xor']},
  'selection.invert':{state:'EXECUTABLE',primitives:['mask.invert']},
  'selection.feather':{state:'EXECUTABLE',primitives:['mask.feather']},
  'selection.grow':{state:'EXECUTABLE',primitives:['mask.morphology.grow']},
  'selection.shrink':{state:'EXECUTABLE',primitives:['mask.morphology.shrink']},
  'selection.open':{state:'EXECUTABLE',primitives:['mask.morphology.open']},
  'selection.close':{state:'EXECUTABLE',primitives:['mask.morphology.close']},
  'transform.perspective':{state:'EXECUTABLE',primitives:['transform.homography','transform.projective-warp']},
  'transform.displacement':{state:'EXECUTABLE',primitives:['transform.displacement-warp']},
  'effects.stack':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag'],truth:'graph compilation is executable; individual graph nodes execute only where matching hands exist'},
  'retouch.perspective-clone':{state:'EXECUTABLE',primitives:['transform.homography','transform.projective-warp','creative.brush.clone']},
  'smart.adjustment-layer':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag','mask.reference']},
  'smart.filter-stack':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag','source-linked-node','mask.reference']},
  'material.smart-mask':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag','mask.reference','material-channel-reference']},
};
const handRecipe=new Map();
for(const hand of Hands.list()){
  const prefix=hand.family==='adjust'?'colour':hand.family;
  const id=prefix+'.'+hand.operation;
  handRecipe.set(id,hand.id);
  definitions[id]={state:'EXECUTABLE',primitives:[hand.id],truth:'Executed through the UC creative-hand registry.'};
}
Object.freeze(definitions);
function registry(){const tools=Object.entries(definitions).map(([id,value])=>({id,state:value.state,primitives:value.primitives,truth:value.truth||null}));const result={schema:REGISTRY_SCHEMA,version:'2.0.0',principle:'human product concepts are decomposed into UC-native deterministic primitives and executable hands; no product UI or implementation is copied',tools,count:tools.length,executable_hands:Hands.audit().total};result.digest=U.sha256(result);return result;}
function receipt(id,state,primitive,result){const value={schema:RECIPE_SCHEMA,version:'2.0.0',tool_id:id,state,primitive,result};value.digest=U.sha256(value);return value;}
function invoke(id,args){id=U.text(id,100,'creative tool id');const definition=definitions[id];U.ensure(definition,'unknown creative tool recipe: '+id);args=args||{};
  if(handRecipe.has(id)){const handId=handRecipe.get(id);return receipt(id,definition.state,handId,Hands.invoke(handId,args));}
  if(id==='selection.rectangle'||id==='selection.ellipse'||id==='selection.polygon'){const kind=id.split('.')[1];return receipt(id,definition.state,'mask.shape.'+kind,P.shapeMask(Object.assign({},args,{kind})));}
  if(id==='selection.magic-wand')return receipt(id,definition.state,'raster.contiguous-colour-mask',R.contiguousColourMask(args.image,args.spec));
  if(id==='selection.colour-range')return receipt(id,definition.state,'raster.colour-range-mask',R.colourRangeMask(args.image,args.spec));
  if(id==='selection.luminance')return receipt(id,definition.state,'raster.luminance-range-mask',R.luminanceRangeMask(args.image,args.spec));
  if(id==='selection.channel')return receipt(id,definition.state,'raster.channel-mask',R.channelMask(args.image,args.channel));
  if(id==='selection.edge')return receipt(id,definition.state,'raster.sobel-edge-mask',R.edgeMask(args.image,args.spec));
  if(['selection.union','selection.intersection','selection.subtract','selection.xor'].includes(id)){const operation=id.split('.')[1];return receipt(id,definition.state,'mask.combine.'+operation,P.combineMasks(args.left,args.right,operation));}
  if(id==='selection.invert')return receipt(id,definition.state,'mask.invert',P.invertMask(args.mask));
  if(id==='selection.feather')return receipt(id,definition.state,'mask.feather',P.featherMask(args.mask,args.radius,args.passes));
  if(['selection.grow','selection.shrink','selection.open','selection.close'].includes(id)){const operation=id.split('.')[1];return receipt(id,definition.state,'mask.morphology.'+operation,P.morphology(args.mask,operation,args.radius));}
  if(id==='transform.perspective'){const h=args.matrix?{matrix:args.matrix,digest:U.sha256(args.matrix)}:T.homography(args.source,args.destination);const warped=T.warp(args.image,{matrix:h.matrix,width:args.width,height:args.height,interpolation:args.interpolation,boundary:args.boundary});return receipt(id,definition.state,'transform.projective-warp',{homography:h,warp:warped});}
  if(id==='transform.displacement')return receipt(id,definition.state,'transform.displacement-warp',T.displacementWarp(args.image,args.spec));
  if(id==='retouch.perspective-clone'){const h=args.matrix?{matrix:args.matrix,digest:U.sha256(args.matrix)}:T.homography(args.source,args.destination);const warped=T.warp(args.image,{matrix:h.matrix,width:args.image.width,height:args.image.height,interpolation:args.interpolation||'bilinear',boundary:args.boundary||'transparent'});const brush=Object.assign({},args.brush||{}, {operator:'clone'});const plan=args.plan||P.brushPlan(brush);const executed=Hands.invoke('creative.brush.clone',{image:args.image,plan,spec:Object.assign({},args.spec||{},{source_image:warped,source_offset:{x:0,y:0}})});return receipt(id,definition.state,'creative.brush.clone',{homography:h,source_warp:warped.digest,execution:executed});}
  if(id==='effects.stack'||id==='smart.adjustment-layer'||id==='smart.filter-stack'||id==='material.smart-mask')return receipt(id,definition.state,'effects.compile-dag',P.effectGraph(args.graph));
  throw new Error('creative recipe exists but has no invocation path: '+id);
}
module.exports={RECIPE_SCHEMA,REGISTRY_SCHEMA,registry,invoke};
