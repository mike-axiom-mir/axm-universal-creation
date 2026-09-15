'use strict';

const U=require('./foundation-utils');
const P=require('./creative-precision');
const Raster=require('./precision-raster-operators');
const Vector=require('./precision-vector-ops');
const Pixel=require('./precision-pixel-art');

const HAND_SCHEMA='axm.creative-executable-hand/v1';
const RESULT_SCHEMA='axm.creative-executable-hand-result/v1';
const ADJUSTMENTS=['brightness','contrast','gamma','exposure','saturation','vibrance','hue','grayscale','invert','threshold','posterize','tint','levels','curves','channel-mixer','gradient-map','white-balance'];
const FILTERS=['box-blur','gaussian-blur','median-blur','pixelate','noise','grain','edge-detect','emboss','sharpen','high-pass','convolution'];
const BRUSHES=['paint','erase','replace-colour','dodge','burn','saturate','desaturate','blur','sharpen','clone','heal','smudge'];
const RETOUCH=['clone','heal'];
const VECTORS=['affine','quadratic','arc','simplify','smooth','regular-polygon','star','stroke-outline','rounded-rect'];
const PIXELS=['palette-quantize','ordered-dither','error-diffusion','spritesheet','tilemap'];
function title(id){return id.split(/[.-]/).map((v)=>v.charAt(0).toUpperCase()+v.slice(1)).join(' ');}
function descriptor(family,operation,fn,outputs){const id='creative.'+family+'.'+operation;const value={schema:HAND_SCHEMA,version:'1.0.0',id,title:title(operation),family,operation,state:'EXECUTABLE',deterministic:true,function:fn,outputs:outputs||['application/json'],truth:'Executable UC-native deterministic operation; product influence is conceptual only and no external product code or UI is embedded.'};value.digest=U.sha256(value);return Object.freeze(value);}
const DESCRIPTORS=Object.freeze([
  ...ADJUSTMENTS.map((op)=>descriptor('adjust',op,'applyAdjustment',['axm.precision-raster/v1'])),
  ...FILTERS.map((op)=>descriptor('filter',op,'filter',['axm.precision-raster/v1'])),
  ...BRUSHES.map((op)=>descriptor('brush',op,'brushApply',['axm.precision-raster/v1','axm.precision-raster-operation/v1'])),
  ...RETOUCH.map((op)=>descriptor('retouch',op,'maskedRetouch',['axm.precision-raster/v1'])),
  ...VECTORS.map((op)=>descriptor('vector',op,op,['axm.precision-vector-path/v1'])),
  ...PIXELS.map((op)=>descriptor('pixel',op,op,['axm.precision-raster/v1'])),
]);
const BY_ID=new Map(DESCRIPTORS.map((d)=>[d.id,d]));
function list(){return DESCRIPTORS.map((d)=>JSON.parse(JSON.stringify(d)));}
function get(id){const d=BY_ID.get(String(id||''));return d?JSON.parse(JSON.stringify(d)):null;}
function wrap(hand,result){const value={schema:RESULT_SCHEMA,version:'1.0.0',status:'EXECUTED',hand_id:hand.id,hand_digest:hand.digest,result};value.digest=U.sha256(value);return value;}
function invoke(id,args){const hand=BY_ID.get(String(id||''));U.ensure(hand,'unknown creative executable hand: '+id);args=args||{};let result;
  if(hand.family==='adjust')result=Raster.applyAdjustment(args.image,Object.assign({},args.spec||{},{type:hand.operation}));
  else if(hand.family==='filter')result=Raster.filter(args.image,Object.assign({},args.spec||{},{type:hand.operation}));
  else if(hand.family==='brush'){const brush=Object.assign({},args.brush||{});brush.operator=hand.operation;const plan=args.plan||P.brushPlan(brush);result=Raster.brushApply(args.image,plan,Object.assign({},args.spec||{},{mode:hand.operation}));}
  else if(hand.family==='retouch')result=Raster.maskedRetouch(args.image,Object.assign({},args.spec||{},{mode:hand.operation,mask:args.mask||(args.spec&&args.spec.mask),source_image:args.source_image||(args.spec&&args.spec.source_image)}));
  else if(hand.family==='vector'){
    if(hand.operation==='affine')result=Vector.affine(args.path,args.matrix,args.id);
    else if(hand.operation==='quadratic')result=Vector.quadratic(args.spec||args);
    else if(hand.operation==='arc')result=Vector.arc(args.spec||args);
    else if(hand.operation==='simplify')result=Vector.simplify(args.spec||args);
    else if(hand.operation==='smooth')result=Vector.smooth(args.spec||args);
    else if(hand.operation==='regular-polygon')result=Vector.regularPolygon(args.spec||args);
    else if(hand.operation==='star')result=Vector.star(args.spec||args);
    else if(hand.operation==='stroke-outline')result=Vector.strokeOutline(args.spec||args);
    else if(hand.operation==='rounded-rect')result=Vector.roundedRect(args.spec||args);
  } else if(hand.family==='pixel'){
    if(hand.operation==='palette-quantize')result=Pixel.quantize(args.image,args.palette);
    else if(hand.operation==='ordered-dither')result=Pixel.orderedDither(args.image,args.palette,args.spec);
    else if(hand.operation==='error-diffusion')result=Pixel.errorDiffusion(args.image,args.palette);
    else if(hand.operation==='spritesheet')result=Pixel.spriteSheet(args.frames,args.spec);
    else if(hand.operation==='tilemap')result=Pixel.tilemap(args.tiles,args.map,args.spec);
  }
  U.ensure(result!=null,'creative hand has no execution path: '+hand.id);return wrap(hand,result);
}
function audit(){const by_family={};DESCRIPTORS.forEach((d)=>{by_family[d.family]=(by_family[d.family]||0)+1;});const result={schema:'axm.creative-executable-hand-audit/v1',version:'1.0.0',total:DESCRIPTORS.length,counts:{EXECUTABLE:DESCRIPTORS.length},by_family,ids:DESCRIPTORS.map((d)=>d.id)};result.digest=U.sha256(result);return result;}
module.exports={HAND_SCHEMA,RESULT_SCHEMA,ADJUSTMENTS,FILTERS,BRUSHES,RETOUCH,VECTORS,PIXELS,list,get,invoke,audit};
