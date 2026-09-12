// Executes generated game logic with a small DOM/canvas double, not a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function node() {
  const handlers = {};
  return {handlers, disabled:false, textContent:'', addEventListener(name,fn){(handlers[name]??=[]).push(fn);},
    emit(name,event={}){for(const fn of handlers[name]||[])fn({target:this,button:0,pointerId:1,detail:1,preventDefault(){},...event});},
    focus(){},setPointerCapture(){},getBoundingClientRect(){return {left:0,top:0,width:960,height:540};}};
}
const ids = ['game','status','sessionButton','reloadButton','resetButton','fireButton','targetButton','targetName','targetHealth','towerValue','scoreValue','ammoValue'];
const nodes = Object.fromEntries(ids.map(id=>[id,node()]));
const context = new Proxy({}, {get:(o,k)=>o[k]??(k==='createRadialGradient'?()=>({addColorStop(){}}):()=>{}),set:(o,k,v)=>(o[k]=v,true)});
nodes.game.width=960;nodes.game.height=540;nodes.game.getContext=()=>context;
const touch = ['ArrowUp','ArrowLeft','ArrowDown','ArrowRight'].map(key=>Object.assign(node(),{dataset:{key}}));
const doc = Object.assign(node(),{hidden:false,querySelector:s=>nodes[s.slice(1)],querySelectorAll:()=>touch});
const win = node();
let statusTool;
doc.modelContext={registerTool(tool){statusTool=tool;}};
class Audio {cloneNode(){return new Audio();}play(){return Promise.reject(new Error('Audio denied in test'));}}
const sandbox=vm.createContext({document:doc,window:win,Audio,AbortController,requestAnimationFrame(){},console:{info(){}}});
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),sandbox);
const read=code=>vm.runInContext(code,sandbox);
const key=(k,extra={})=>win.emit('keydown',{target:nodes.game,key:k,repeat:false,...extra});
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
// Blur pauses and clears input. Resume must not keep firing or moving.
key('d');win.emit('blur');assert.equal(read('state.phase'),'paused');assert.equal(read('keys.size'),0);
const x=read('state.player.x');const stoppedAmmo=read('state.ammo');nodes.sessionButton.emit('click');read('update(0.25)');
assert.equal(read('state.player.x'),x);assert.equal(read('state.ammo'),stoppedAmmo);
// Paused timers and positions remain unchanged, including a held pointer.
nodes.game.emit('pointerdown',{clientX:480,clientY:100});nodes.sessionButton.emit('click');
assert.equal(read('pointerHeld'),false);const paused=read('JSON.stringify(state)');read('update(5)');assert.equal(read('JSON.stringify(state)'),paused);
// Pointer cancellation and reset release every input source.
nodes.sessionButton.emit('click');touch[3].emit('pointerdown');assert.equal(read('keys.has("ArrowRight")'),true);
touch[3].emit('lostpointercapture');assert.equal(read('keys.size'),0);
nodes.fireButton.emit('pointerdown');assert.equal(read('targetHeld'),true);nodes.fireButton.emit('pointercancel');assert.equal(read('targetHeld'),false);
key('d');nodes.resetButton.emit('click');assert.equal(read('state.phase'),'ready');assert.equal(read('keys.size'),0);
// Visibility loss pauses; restored visibility never starts the session by itself.
nodes.sessionButton.emit('click');doc.hidden=true;doc.emit('visibilitychange');assert.equal(read('state.phase'),'paused');doc.hidden=false;doc.emit('visibilitychange');assert.equal(read('state.phase'),'paused');
// Terminal states clear shooting and replay starts from fresh score/ammunition.
nodes.sessionButton.emit('click');key(' ');read('state.tower.health=0; update(0.01)');assert.equal(read('state.phase'),'lost');assert.equal(read('keys.size'),0);
nodes.sessionButton.emit('click');assert.equal(read('state.phase'),'playing');assert.equal(read('state.score'),0);assert.equal(read('state.ammo'),read('SPEC.rules.ammo_capacity'));
read('state.enemies.forEach(e=>e.alive=false);update(0.01)');assert.equal(read('state.phase'),'won');assert.equal(nodes.targetButton.disabled,true);
setImmediate(()=>console.log('GENERATED_GAME_LOGIC_OK (DOM/canvas doubles; no visual/browser claim)'));
