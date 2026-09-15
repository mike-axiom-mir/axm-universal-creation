'use strict';

const U=require('./foundation-utils');
const P=require('./creative-precision');
const R=require('./precision-raster');
const T=require('./precision-transform');

const RECIPE_SCHEMA='axm.creative-tool-recipe/v1';
const REGISTRY_SCHEMA='axm.creative-tool-recipe-registry/v1';

const definitions=Object.freeze({
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
  'effects.stack':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag'],truth:'graph compilation is executable; individual effect rendering remains delegated to matching effect hands'},
  'brush.paint':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','paint.operator'],truth:'deterministic dabs and dynamics are executable; pixel paint application remains a renderer/hand concern'},
  'brush.erase':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','erase.operator']},
  'brush.smudge':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','smudge.operator']},
  'brush.clone':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','source-sampler','clone.operator']},
  'brush.heal':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','source-sampler','heal.operator']},
  'brush.blur':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','blur.operator']},
  'brush.sharpen':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','sharpen.operator']},
  'brush.dodge':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','exposure.operator']},
  'brush.burn':{state:'PLAN_EXECUTABLE',primitives:['brush.plan-dabs','exposure.operator']},
  'retouch.perspective-clone':{state:'PLAN_EXECUTABLE',primitives:['transform.homography','brush.plan-dabs','source-sampler','clone.operator']},
  'smart.adjustment-layer':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag','mask.reference']},
  'smart.filter-stack':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag','source-linked-node','mask.reference']},
  'material.smart-mask':{state:'EXECUTABLE_CONTRACT',primitives:['effects.compile-dag','mask.reference','material-channel-reference']},
});
function registry(){const tools=Object.entries(definitions).map(([id,value])=>({id,state:value.state,primitives:value.primitives,truth:value.truth||null}));const result={schema:REGISTRY_SCHEMA,version:'1.0.0',principle:'human product names are decomposed into AXM-native deterministic primitives; no product UI or implementation is copied',tools,count:tools.length};result.digest=U.sha256(result);return result;}
function receipt(id,state,primitive,result){const value={schema:RECIPE_SCHEMA,version:'1.0.0',tool_id:id,state,primitive,result};value.digest=U.sha256(value);return value;}
function invoke(id,args){id=U.text(id,100,'creative tool id');const definition=definitions[id];U.ensure(definition,'unknown creative tool recipe: '+id);args=args||{};
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
  if(id==='effects.stack'||id==='smart.adjustment-layer'||id==='smart.filter-stack'||id==='material.smart-mask')return receipt(id,definition.state,'effects.compile-dag',P.effectGraph(args.graph));
  if(id.startsWith('brush.')||id==='retouch.perspective-clone'){const operator=id==='retouch.perspective-clone'?'clone':id.split('.')[1];const plan=P.brushPlan(Object.assign({},args.brush||args,{operator}));const extra=id==='retouch.perspective-clone'?(args.matrix?{matrix:args.matrix,digest:U.sha256(args.matrix)}:T.homography(args.source,args.destination)):null;return receipt(id,definition.state,'brush.plan-dabs',{plan,transform:extra,missing_execution:definition.primitives.filter((item)=>!['brush.plan-dabs','transform.homography'].includes(item))});}
  throw new Error('creative recipe exists but has no invocation path: '+id);
}
module.exports={RECIPE_SCHEMA,REGISTRY_SCHEMA,registry,invoke};
