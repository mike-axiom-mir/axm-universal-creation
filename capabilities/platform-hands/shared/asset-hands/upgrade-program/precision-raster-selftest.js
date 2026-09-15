'use strict';
const assert=require('assert');const R=require('./precision-raster');const T=require('./precision-transform');const P=require('./creative-precision');
const rgba=Buffer.alloc(8*8*4);for(let y=0;y<8;y++)for(let x=0;x<8;x++){const i=(y*8+x)*4;rgba[i]=x<4?255:0;rgba[i+1]=y<4?255:0;rgba[i+2]=0;rgba[i+3]=255;}
const img=R.image({width:8,height:8,rgba});const red=R.channelMask(img,'red');const colour=R.colourRangeMask(img,{target_rgb:[255,255,0],tolerance:1});const contiguous=R.contiguousColourMask(img,{x:1,y:1,tolerance:1,connectivity:4});const edge=R.edgeMask(img,{threshold:.05,softness:.1});
assert.equal(P.decodeMask(red).alpha.length,64);assert.equal(P.decodeMask(colour).alpha.filter((v)=>v===255).length,16);assert.equal(P.decodeMask(contiguous).alpha.filter((v)=>v===255).length,16);assert(P.decodeMask(edge).alpha.some((v)=>v>0));
const h=T.homography([{x:0,y:0},{x:8,y:0},{x:8,y:8},{x:0,y:8}],[{x:1,y:0},{x:7,y:1},{x:8,y:7},{x:0,y:8}]);const p=T.transformPoint(h.matrix,{x:0,y:0});assert(Math.abs(p.x-1)<1e-8&&Math.abs(p.y)<1e-8);const warped=T.warp(img,{matrix:h.matrix,width:8,height:8,interpolation:'bilinear',boundary:'transparent'});assert.equal(R.decode(warped.image).rgba.length,256);assert.equal(warped.receipt.status,'PASS');
const disp=T.displacementWarp(img,{dx:Array(64).fill(1),dy:Array(64).fill(0),scale:1,interpolation:'nearest',boundary:'clamp'});assert.equal(disp.receipt.status,'PASS');
console.log(JSON.stringify({status:'PASS',image:img.digest,edge:edge.digest,homography:h.digest,warp:warped.image.digest,displacement:disp.image.digest},null,2));
