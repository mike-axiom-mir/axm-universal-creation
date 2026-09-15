'use strict';
const assert=require('assert');const Recipes=require('./creative-recipes');const Raster=require('./precision-raster');const P=require('./creative-precision');
const rgba=Buffer.alloc(4*4*4);for(let i=0;i<16;i++){rgba[i*4]=i<8?255:0;rgba[i*4+3]=255;}const image=Raster.image({width:4,height:4,rgba});
const wand=Recipes.invoke('selection.magic-wand',{image,spec:{x:0,y:0,tolerance:0,connectivity:4}});assert.equal(wand.state,'EXECUTABLE');assert(P.decodeMask(wand.result).alpha.some((v)=>v===255));
const perspective=Recipes.invoke('transform.perspective',{image,source:[{x:0,y:0},{x:4,y:0},{x:4,y:4},{x:0,y:4}],destination:[{x:0,y:0},{x:4,y:0},{x:3,y:4},{x:1,y:4}]});assert.equal(perspective.state,'EXECUTABLE');assert.equal(perspective.result.warp.receipt.status,'PASS');
const dodge=Recipes.invoke('brush.dodge',{id:'dodge',size:4,samples:[{x:0,y:0,pressure:.5,time_ms:0},{x:10,y:0,pressure:1,time_ms:10}]});assert.equal(dodge.state,'PLAN_EXECUTABLE');assert(dodge.result.missing_execution.includes('exposure.operator'));
const stack=Recipes.invoke('smart.adjustment-layer',{graph:{nodes:[{id:'source',op:'source'},{id:'curve',op:'curves',inputs:['source'],mask_id:'m'}]}});assert.equal(stack.state,'EXECUTABLE_CONTRACT');
const registry=Recipes.registry();assert(registry.count>=30);assert(registry.tools.some((tool)=>tool.id==='retouch.perspective-clone'));
console.log(JSON.stringify({status:'PASS',recipes:registry.count,wand:wand.digest,perspective:perspective.digest,dodge:dodge.digest,stack:stack.digest},null,2));
