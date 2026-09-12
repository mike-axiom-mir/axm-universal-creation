// Executes generated game logic with a small DOM/canvas double, not a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function node() {
  const handlers = {};
  return {handlers, tagName:'BUTTON',disabled:false, textContent:'', addEventListener(name,fn){(handlers[name]??=[]).push(fn);},
    emit(name,event={}){for(const fn of handlers[name]||[])fn({target:this,button:0,pointerId:1,detail:1,preventDefault(){},...event});},
    focus(){},setPointerCapture(){},getBoundingClientRect(){return {left:0,top:0,width:960,height:540};}};
}
const ids = ['game','status','sessionButton','reloadButton','resetButton','fireButton','targetButton','targetName','targetHealth','towerValue','scoreValue','ammoValue','constructionBalance','constructionIncome','constructionCount','cancelBuild','buildMessage','waveValue'];
const nodes = Object.fromEntries(ids.map(id=>[id,node()]));
const drawCalls={};
const context = new Proxy({}, {get:(o,k)=>o[k]??((...args)=>{drawCalls[k]=(drawCalls[k]||0)+1;if(['createRadialGradient','createLinearGradient'].includes(k))return {addColorStop(){}};}),set:(o,k,v)=>(o[k]=v,true)});
function resetDrawCalls(){for(const k of Object.keys(drawCalls))delete drawCalls[k];}
function totalDrawCalls(){return Object.values(drawCalls).reduce((a,b)=>a+b,0);}
let cacheCopies=0,cacheAllocations=0;
function createCacheCanvas(){cacheAllocations++;return {width:0,height:0,getContext(){return {drawImage(source){assert.equal(source,nodes.game);cacheCopies++;}};}};}

nodes.game.tagName='CANVAS';nodes.game.width=960;nodes.game.height=540;nodes.game.getContext=()=>context;
const touch = ['ArrowUp','ArrowLeft','ArrowDown','ArrowRight'].map(key=>Object.assign(node(),{dataset:{key}}));
const buildButtons=['generator','turret','repair'].map(kind=>Object.assign(node(),{dataset:{build:kind},setAttribute(){}}));
const doc = Object.assign(node(),{hidden:false,createElement:createCacheCanvas,querySelector:s=>nodes[s.slice(1)],querySelectorAll:s=>s==='[data-build]'?buildButtons:touch});
const win = node();
win.devicePixelRatio=2;
let statusTool;
doc.modelContext={registerTool(tool){statusTool=tool;}};
class Audio {cloneNode(){return new Audio();}play(){return Promise.reject(new Error('Audio denied in test'));}}
class Image {constructor(){this.complete=false;this.naturalWidth=0;}}
const sandbox=vm.createContext({document:doc,window:win,Audio,Image,AbortController,requestAnimationFrame(){},console:{info(){}}});
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),sandbox);
const read=code=>vm.runInContext(code,sandbox);
const key=(k,extra={})=>win.emit('keydown',{target:nodes.game,key:k,repeat:false,...extra});
// Static rendering work is reused; it never changes canonical gameplay state.
const canonicalBefore=read('JSON.stringify(state)');
read('deckCache=null');resetDrawCalls();read('drawDeck()');const uncachedCommands=totalDrawCalls();
const copiesBefore=cacheCopies;resetDrawCalls();read('drawDeck()');const cachedCommands=totalDrawCalls();
assert.ok(uncachedCommands>100);assert.equal(cachedCommands,1);assert.equal(drawCalls.drawImage,1);
assert.equal(cacheCopies,copiesBefore);assert.equal(read('JSON.stringify(state)'),canonicalBefore);
// A texture arriving after the first frame must replace the untextured cache.
read('deckTexture.complete=true;deckTexture.naturalWidth=96;drawDeck()');assert.equal(cacheCopies,copiesBefore+1);
read('drawDeck()');assert.equal(cacheCopies,copiesBefore+1);
// Reset does not retain ghosts, reallocate the scenery, or change color intent.
const resetCopies=cacheCopies;read('reset()');assert.equal(cacheCopies,resetCopies);
assert.equal(read('shadeColor("#12345680",0)'), '#12345680');
assert.equal(read('shadeColor("#12345680",-1)'), '#00000080');
assert.equal(read('shadeColor("#12345680",1)'), '#ffffff80');
assert.equal(read('playerPaint.top'),read('shadeColor(SPEC.player.color,-.18)'));
assert.equal(read('relayPaint.top'),read('shadeColor(SPEC.tower.color,.25)'));
// Cache allocation failures keep the direct renderer usable without retrying.
let failedAllocations=0;doc.createElement=()=>{failedAllocations++;return {getContext(){return null;}};};
read('deckCache=null;deckCacheUnavailable=false;drawDeck()');resetDrawCalls();read('drawDeck()');
assert.equal(failedAllocations,1);assert.ok(totalDrawCalls()>100);assert.equal(read('JSON.stringify(state)'),canonicalBefore);
doc.createElement=createCacheCanvas;read('deckCache=null;deckCacheUnavailable=false;reset()');
console.log(`STATIC_DECK_COMMANDS uncached=${uncachedCommands} cached=${cachedCommands} (call counts, not frame time)`);
// High-DPI backing pixels must not change world limits or pointer picking.
assert.equal(nodes.game.width,1920);assert.equal(nodes.game.height,1080);
for(const [x,y] of [[0,0],[480,270],[960,540],[123,419]]){
  const result=read(`unproject(project(${x},${y}).x,project(${x},${y}).y)`);
  assert.ok(Math.abs(result.x-x)<1e-8 && Math.abs(result.y-y)<1e-8);
  const aim=read(`pointerPosition({clientX:project(${x},${y},21).x,clientY:project(${x},${y},21).y})`);
  assert.ok(Math.abs(aim.x-x)<1e-8 && Math.abs(aim.y-y)<1e-8);
}
read('burst(10,20,"#ffffff",250)');assert.equal(read('state.fx.length'),180);
read('reset()');assert.equal(read('state.fx.length'),0);
assert.equal(read('state.phase'),'ready');
assert.equal(statusTool.name,'read_arena_status');
assert.equal(statusTool.annotations.readOnlyHint,true);
assert.equal(statusTool.execute({}).ammo,'30 / 30');
assert.throws(()=>statusTool.execute({play:true}),/empty object/);
assert.equal(nodes.fireButton.disabled,true);
nodes.sessionButton.emit('click');
assert.equal(read('state.phase'),'playing');
// One held input produces multiple shots with cooldown and target cycling.
const first=read('state.selectedId');key('q');assert.notEqual(read('state.selectedId'),first);
const second=read('state.selectedId');key('q',{repeat:true});assert.equal(read('state.selectedId'),second);
key(' ');read('update(0.01)');const ammo=read('state.ammo');read('update(0.2)');assert.equal(read('state.ammo'),ammo-1);
// Native focused controls must not inject movement or shooting.
win.emit('keyup',{key:' '});win.emit('keydown',{target:nodes.resetButton,key:' '});assert.equal(read('keys.has(" ")'),false);
// Focus on Next target must not swallow WASD; editable fields stay native.
win.emit('keydown',{target:nodes.targetButton,key:'d'});
const focusX=read('state.player.x');read('update(0.1)');assert.ok(read('state.player.x')>focusX);
win.emit('keyup',{key:'d'});
win.emit('keydown',{target:{tagName:'INPUT'},key:'a'});assert.equal(read('keys.has("a")'),false);
// Simultaneous touch movement/fire advances position and consumes ammunition.
read('state.fireCooldown=0');touch[3].emit('pointerdown');nodes.fireButton.emit('pointerdown');
const touchX=read('state.player.x'), touchAmmo=read('state.ammo');read('update(0.2)');
assert.ok(read('state.player.x')>touchX);assert.ok(read('state.ammo')<touchAmmo);
// Touch release does not cancel a keyboard holding the same direction.
key('ArrowRight');touch[3].emit('pointerup');assert.equal(read('keys.has("ArrowRight")'),true);
win.emit('keyup',{key:'ArrowRight'});nodes.fireButton.emit('pointerup');
// A quick Space tap between frames still fires one shot.
read('state.fireCooldown=0');const tapAmmo=read('state.ammo');key(' ');win.emit('keyup',{key:' '});assert.equal(read('state.ammo'),tapAmmo-1);
// Blur pauses and clears input. Resume must not keep firing or moving.
key('d');win.emit('blur');assert.equal(read('state.phase'),'paused');assert.equal(read('keys.size'),0);
const x=read('state.player.x');const stoppedAmmo=read('state.ammo');nodes.sessionButton.emit('click');read('update(0.25)');
assert.equal(read('state.player.x'),x);assert.equal(read('state.ammo'),stoppedAmmo);
// Paused timers and positions remain unchanged, including a held pointer.
nodes.game.emit('pointerdown',{clientX:480,clientY:100});nodes.sessionButton.emit('click');
assert.equal(read('pointerHeld'),false);const paused=read('JSON.stringify(state)');read('update(5)');assert.equal(read('JSON.stringify(state)'),paused);
// Pointer cancellation and reset release every input source.
nodes.sessionButton.emit('click');touch[3].emit('pointerdown');assert.equal(read('touchKeys.has("ArrowRight")'),true);
touch[3].emit('lostpointercapture');assert.equal(read('touchKeys.size'),0);
nodes.fireButton.emit('pointerdown');assert.equal(read('targetHeld'),true);nodes.fireButton.emit('pointercancel');assert.equal(read('targetHeld'),false);
key('d');nodes.resetButton.emit('click');assert.equal(read('state.phase'),'ready');assert.equal(read('keys.size'),0);
// Visibility loss pauses; restored visibility never starts the session by itself.
nodes.sessionButton.emit('click');doc.hidden=true;doc.emit('visibilitychange');assert.equal(read('state.phase'),'paused');doc.hidden=false;doc.emit('visibilitychange');assert.equal(read('state.phase'),'paused');
// Terminal states clear shooting and replay starts from fresh score/ammunition.
nodes.sessionButton.emit('click');key(' ');read('state.tower.health=0; update(0.01)');assert.equal(read('state.phase'),'lost');assert.equal(read('keys.size'),0);
nodes.sessionButton.emit('click');assert.equal(read('state.phase'),'playing');assert.equal(read('state.score'),0);assert.equal(read('state.ammo'),read('SPEC.rules.ammo_capacity'));
read('if(SPEC.waves)state.waveIndex=SPEC.waves.count-1;state.enemies.forEach(e=>e.alive=false);update(0.01)');assert.equal(read('state.phase'),'won');assert.equal(nodes.targetButton.disabled,true);
if(read('Boolean(SPEC.construction)')){
  read('reset();transition("start")');
  for(const [kind,col,row] of [['generator',1,1],['turret',2,1],['repair',6,3]])assert.equal(read(`Construction.place(SPEC.construction,state.construction,'${kind}',${col},${row}).ok`),true);
  read('state.enemies.forEach(e=>e.alive=false);Object.assign(state.enemies[0],{alive:true,x:150,y:150,health:1000,speed:0,damage:0});state.tower.health=state.tower.max_health-20;update(1)');
  assert.equal(read('state.construction.credits'),6);assert.equal(read('state.enemies[0].health'),975);assert.equal(read('state.tower.health'),read('state.tower.max_health-15'));
  read('transition("pause")');const before=read('JSON.stringify(state)');read('update(10)');assert.equal(read('JSON.stringify(state)'),before);
  read('reset()');assert.equal(read('state.construction.buildings.length'),0);assert.equal(read('state.construction.credits'),200);
}
if(read('Boolean(SPEC.waves)')){
  read('reset();transition("start");Construction.place(SPEC.construction,state.construction,"generator",1,1);state.tower.health-=25;state.player.x=300;state.ammo=2;state.enemies.forEach(e=>e.alive=false);update(0)');
  assert.equal(read('state.phase'),'paused');assert.equal(read('state.betweenWaves'),true);assert.equal(nodes.sessionButton.textContent,'Launch wave 2');
  assert.equal(read('state.construction.credits'),200);
  const intermission=read('JSON.stringify(state)');read('completeWave();update(10)');key('p');win.emit('keyup',{key:'p'});
  assert.equal(read('JSON.stringify(state)'),intermission);
  assert.equal(read('placementCheck("turret",Math.floor(SPEC.enemies[0].x/SPEC.construction.cell_size),Math.floor(SPEC.enemies[0].y/SPEC.construction.cell_size)).ok'),false);
  nodes.sessionButton.emit('click');assert.equal(read('state.waveIndex'),1);assert.equal(read('state.phase'),'playing');
  assert.equal(read('state.construction.buildings.length'),1);assert.equal(read('state.player.x'),300);assert.equal(read('state.tower.health'),read('SPEC.tower.max_health-25'));
  assert.equal(read('state.ammo'),read('SPEC.rules.ammo_capacity'));assert.equal(read('state.enemies[0].maxHealth'),read('Math.round(SPEC.enemies[0].health*1.25)'));
  read('state.enemies.forEach(e=>e.alive=false);update(0)');nodes.sessionButton.emit('click');assert.equal(read('state.waveIndex'),2);
  read('state.enemies.forEach(e=>e.alive=false);update(0)');assert.equal(read('state.phase'),'won');assert.equal(read('state.wavesCleared'),3);assert.equal(read('state.construction.credits'),320);
  const won=read('JSON.stringify(state)');read('completeWave();update(1)');assert.equal(read('JSON.stringify(state)'),won);
  read('reset();transition("start");state.tower.health=0;state.enemies.forEach(e=>e.alive=false);update(0)');assert.equal(read('state.phase'),'lost');assert.equal(read('state.wavesCleared'),0);
  read('reset()');assert.equal(read('state.waveIndex'),0);assert.equal(read('state.betweenWaves'),false);
}
setImmediate(()=>console.log('GENERATED_GAME_LOGIC_OK (DOM/canvas doubles; no visual/browser claim)'));
