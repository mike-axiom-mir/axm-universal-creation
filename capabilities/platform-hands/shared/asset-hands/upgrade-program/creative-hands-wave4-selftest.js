'use strict';
const assert=require('assert');
const Hands=require('./creative-hands');
const R=require('./precision-raster');
const Platform=require('../../../index');

function raster(width,height,fn){const rgba=Buffer.alloc(width*height*4);for(let y=0;y<height;y++)for(let x=0;x<width;x++){const i=(y*width+x)*4,v=fn(x,y);rgba[i]=v[0];rgba[i+1]=v[1];rgba[i+2]=v[2];rgba[i+3]=v[3]==null?255:v[3];}return R.image({width,height,rgba});}
const base=raster(8,6,(x,y)=>[x*28,y*36,70,255]);
const top=raster(8,6,(x,y)=>[(x+y)%2?220:40,100,180,255]);
const audit=Hands.audit();
assert.equal(audit.total,197);
assert.equal(audit.by_family.composite,14);
assert.equal(audit.by_family['raster-geometry'],10);
assert.equal(audit.by_family.procedural,12);
assert.equal(audit.by_family['audio-dsp'],10);
assert.equal(audit.by_family['timeline-finish'],7);
assert.equal(Platform.creativeHands.audit().total,197);
assert.equal(Platform.creativeHands.recipeRegistry().count,204);

const multiplied=Hands.invoke('creative.composite.multiply',{base,top,spec:{opacity:.65}});
assert.equal(multiplied.result.schema,'axm.precision-composite/v1');
assert.equal(multiplied.result.image.width,8);
assert.notEqual(multiplied.result.image.digest,base.digest);
const rotated=Hands.invoke('creative.raster-geometry.rotate-90',{image:base});
assert.equal(rotated.result.width,6);assert.equal(rotated.result.height,8);
const resized=Hands.invoke('creative.raster-geometry.resize-bilinear',{image:base,spec:{width:4,height:3}});
assert.equal(resized.result.width,4);assert.equal(resized.result.height,3);
const padded=Hands.invoke('creative.raster-geometry.pad',{image:resized.result,spec:{left:1,right:2,top:1,bottom:0,rgba:[1,2,3,255]}});
assert.equal(padded.result.width,7);assert.equal(padded.result.height,4);

const checker=Hands.invoke('creative.procedural.checker',{spec:{width:16,height:16,size:2,a_rgba:[10,20,30,255],b_rgba:[230,220,210,255]}});
assert.equal(checker.result.schema,'axm.precision-raster/v1');
const gradient=Hands.invoke('creative.procedural.linear-gradient',{spec:{width:16,height:16,start_rgba:[0,0,0,255],end_rgba:[255,80,20,255],angle_degrees:30}});
assert.notEqual(gradient.result.digest,checker.result.digest);
const voronoiA=Hands.invoke('creative.procedural.voronoi',{spec:{width:32,height:32,cells:8,seed:'wave4'}});
const voronoiB=Hands.invoke('creative.procedural.voronoi',{spec:{width:32,height:32,cells:8,seed:'wave4'}});
assert.equal(voronoiA.result.digest,voronoiB.result.digest);
assert.throws(()=>Hands.invoke('creative.procedural.voronoi',{spec:{width:512,height:512,cells:128,seed:'too-large'}}),/voronoi work budget exceeded/);

const samples=[];for(let i=0;i<800;i++)samples.push(Math.sin(i/8)*.85,Math.sin(i/11)*.65);
const audio=Hands.invoke('creative.audio.create',{spec:{sample_rate:8000,channels:2,samples}}).result;
const low=Hands.invoke('creative.audio-dsp.lowpass',{audio,spec:{cutoff_hz:900}}).result;
assert.equal(low.schema,'axm.precision-audio/v1');assert.notEqual(low.digest,audio.digest);
const compressed=Hands.invoke('creative.audio-dsp.compressor',{audio,spec:{threshold_db:-12,ratio:4}}).result;
assert(compressed.analysis.sample_peak<=audio.analysis.sample_peak);
const wide=Hands.invoke('creative.audio-dsp.stereo-width',{audio,spec:{width:1.5}}).result;
assert.equal(wide.channels,2);
const echoed=Hands.invoke('creative.audio-dsp.echo',{audio,spec:{seconds:.01,mix:.4,feedback:.3}}).result;
assert.equal(echoed.samples.length,audio.samples.length);

let timeline=Hands.invoke('creative.timeline.create',{spec:{id:'wave4-edit',clips:[{id:'a',source_id:'a.mov',start:0,duration:2},{id:'b',source_id:'b.mov',start:2,duration:3}],captions:[{id:'inside',start:.5,duration:.5,text:'remove'},{id:'later',start:2.5,duration:.5,text:'shift'}]}}).result;
timeline=Hands.invoke('creative.timeline-finish.crossfade',{timeline,spec:{left_id:'a',right_id:'b',duration:.5}}).result;
assert.equal(timeline.transitions.length,1);
timeline=Hands.invoke('creative.timeline-finish.opacity-keyframe',{timeline,spec:{id:'b',time:1,value:.5}}).result;
assert.equal(timeline.clips.find((c)=>c.id==='b').metadata.opacity_keyframes.length,1);
timeline=Hands.invoke('creative.timeline-finish.duplicate',{timeline,spec:{id:'b',new_id:'b-copy',offset_seconds:3}}).result;
assert(timeline.clips.some((c)=>c.id==='b-copy'));
timeline=Hands.invoke('creative.timeline-finish.ripple-delete',{timeline,spec:{id:'a'}}).result;
assert(!timeline.clips.some((c)=>c.id==='a'));assert.equal(timeline.clips.find((c)=>c.id==='b').start,0);assert(!timeline.captions.some((c)=>c.id==='inside'));assert.equal(timeline.captions.find((c)=>c.id==='later').start,.5);assert.equal(timeline.transitions.length,0);

console.log(JSON.stringify({status:'PASS',executable_hands:audit.total,recipes:Platform.creativeHands.recipeRegistry().count,by_family:audit.by_family,composite:multiplied.digest,geometry:padded.digest,procedural:voronoiA.digest,audio:echoed.digest,timeline:timeline.digest},null,2));