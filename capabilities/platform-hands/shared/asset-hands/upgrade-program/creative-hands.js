'use strict';

const U=require('./foundation-utils');
const P=require('./creative-precision');
const RasterBase=require('./precision-raster');
const Raster=require('./precision-raster-operators');
const Transform=require('./precision-transform');
const VectorCore=require('./vector-engine');
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
const SELECTIONS=['rectangle','ellipse','polygon','magic-wand','colour-range','luminance','channel','edge','union','intersection','subtract','xor','invert','feather','grow','shrink','open','close'];
const TRANSFORMS=['homography','projective-warp','displacement-warp','invert-matrix','transform-point'];
const VECTOR_CORE=['split-cubic','join','offset-polyline','boolean-rect','variable-outline','appearance-svg'];
const GRAPHS=['compile'];
function title(id){return id.split(/[.-]/).map((v)=>v.charAt(0).toUpperCase()+v.slice(1)).join(' ');}
function limits(family,operation){
  if(family==='filter'&&['box-blur','gaussian-blur','sharpen','high-pass'].includes(operation))return{radius:{min:1,max:7}};
  if(family==='filter'&&operation==='median-blur')return{radius:{min:1,max:4}};
  if(family==='brush'&&['blur','sharpen'].includes(operation))return{radius:{min:1,max:7}};
  return{};
}
function descriptor(family,operation,fn,outputs){const id='creative.'+family+'.'+operation;const value={schema:HAND_SCHEMA,version:'1.1.0',id,title:title(operation),family,operation,state:'EXECUTABLE',deterministic:true,function:fn,outputs:outputs||['application/json'],limits:limits(family,operation),truth:'Executable UC-native deterministic operation; product influence is conceptual only and no external product code or UI is embedded.'};value.digest=U.sha256(value);return Object.freeze(value);}
const DESCRIPTORS=Object.freeze([
  ...ADJUSTMENTS.map((op)=>descriptor('adjust',op,'applyAdjustment',['axm.precision-raster/v1'])),
  ...FILTERS.map((op)=>descriptor('filter',op,'filter',['axm.precision-raster/v1'])),
  ...BRUSHES.map((op)=>descriptor('brush',op,'brushApply',['axm.precision-raster/v1','axm.precision-raster-operation/v1'])),
  ...RETOUCH.map((op)=>descriptor('retouch',op,'maskedRetouch',['axm.precision-raster/v1'])),
  ...VECTORS.map((op)=>descriptor('vector',op,op,['axm.precision-vector-path/v1'])),
  ...PIXELS.map((op)=>descriptor('pixel',op,op,['axm.precision-raster/v1'])),
  ...SELECTIONS.map((op)=>descriptor('selection',op,op,['axm.precision-mask/v1'])),
  ...TRANSFORMS.map((op)=>descriptor('transform',op,op,['application/json'])),
  ...VECTOR_CORE.map((op)=>descriptor('vector-core',op,op,['application/json'])),
  ...GRAPHS.map((op)=>descriptor('graph',op,'effectGraph',['axm.precision-effect-graph/v1'])),
]);
const BY_ID=new Map(DESCRIPTORS.map((d)=>[d.id,d]));
function list(){return DESCRIPTORS.map((d)=>JSON.parse(JSON.stringify(d)));}
function get(id){const d=BY_ID.get(String(id||''));return d?JSON.parse(JSON.stringify(d)):null;}
function wrap(hand,result){const value={schema:RESULT_SCHEMA,version:'1.1.0',status:'EXECUTED',hand_id:hand.id,hand_digest:hand.digest,result};value.digest=U.sha256(value);return value;}
function boundedSpec(hand,spec){const next=Object.assign({},spec||{}),radius=hand.limits&&hand.limits.radius;if(radius&&next.radius!=null){const value=U.finite(next.radius,hand.id+' radius');U.ensure(value>=radius.min&&value<=radius.max,hand.id+' radius outside '+radius.min+'..'+radius.max);next.radius=value;}return next;}
function invoke(id,args){const hand=BY_ID.get(String(id||''));U.ensure(hand,'unknown creative executable hand: '+id);args=args||{};let result;
  if(hand.family==='adjust')result=Raster.applyAdjustment(args.image,Object.assign({},args.spec||{},{type:hand.operation}));
  else if(hand.family==='filter')result=Raster.filter(args.image,Object.assign(boundedSpec(hand,args.spec),{type:hand.operation}));
  else if(hand.family==='brush'){const brush=Object.assign({},args.brush||{});brush.operator=hand.operation;const plan=args.plan||P.brushPlan(brush);result=Raster.brushApply(args.image,plan,Object.assign(boundedSpec(hand,args.spec),{mode:hand.operation}));}
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
  } else if(hand.family==='selection'){
    if(['rectangle','ellipse','polygon'].includes(hand.operation))result=P.shapeMask(Object.assign({},args.spec||args,{kind:hand.operation}));
    else if(hand.operation==='magic-wand')result=RasterBase.contiguousColourMask(args.image,args.spec);
    else if(hand.operation==='colour-range')result=RasterBase.colourRangeMask(args.image,args.spec);
    else if(hand.operation==='luminance')result=RasterBase.luminanceRangeMask(args.image,args.spec);
    else if(hand.operation==='channel')result=RasterBase.channelMask(args.image,args.channel);
    else if(hand.operation==='edge')result=RasterBase.edgeMask(args.image,args.spec);
    else if(['union','intersection','subtract','xor'].includes(hand.operation))result=P.combineMasks(args.left,args.right,hand.operation);
    else if(hand.operation==='invert')result=P.invertMask(args.mask);
    else if(hand.operation==='feather')result=P.featherMask(args.mask,args.radius,args.passes);
    else if(['grow','shrink','open','close'].includes(hand.operation))result=P.morphology(args.mask,hand.operation,args.radius);
  } else if(hand.family==='transform'){
    if(hand.operation==='homography')result=Transform.homography(args.source,args.destination);
    else if(hand.operation==='projective-warp')result=Transform.warp(args.image,args.spec||args);
    else if(hand.operation==='displacement-warp')result=Transform.displacementWarp(args.image,args.spec||args);
    else if(hand.operation==='invert-matrix')result={matrix:Transform.invert3(args.matrix)};
    else if(hand.operation==='transform-point')result=Transform.transformPoint(args.matrix,args.point);
  } else if(hand.family==='vector-core'){
    if(hand.operation==='split-cubic')result=VectorCore.splitCubic(args.points,args.t);
    else if(hand.operation==='join')result=VectorCore.join(args.left,args.right,args.id,args.tolerance);
    else if(hand.operation==='offset-polyline')result=VectorCore.offsetPolyline(args.points,args.distance,args.id,args.closed===true);
    else if(hand.operation==='boolean-rect')result=VectorCore.booleanRect(args.a,args.b,args.operation,args.id);
    else if(hand.operation==='variable-outline')result={points:VectorCore.variableOutline(args.points,args.widths)};
    else if(hand.operation==='appearance-svg')result=VectorCore.appearanceSvg(args.spec||args);
  } else if(hand.family==='graph')result=P.effectGraph(args.graph||args);
  U.ensure(result!=null,'creative hand has no execution path: '+hand.id);return wrap(hand,result);
}
function audit(){const by_family={};DESCRIPTORS.forEach((d)=>{by_family[d.family]=(by_family[d.family]||0)+1;});const result={schema:'axm.creative-executable-hand-audit/v1',version:'1.1.0',total:DESCRIPTORS.length,counts:{EXECUTABLE:DESCRIPTORS.length},by_family,ids:DESCRIPTORS.map((d)=>d.id)};result.digest=U.sha256(result);return result;}
module.exports={HAND_SCHEMA,RESULT_SCHEMA,ADJUSTMENTS,FILTERS,BRUSHES,RETOUCH,VECTORS,PIXELS,SELECTIONS,TRANSFORMS,VECTOR_CORE,GRAPHS,list,get,invoke,audit};
