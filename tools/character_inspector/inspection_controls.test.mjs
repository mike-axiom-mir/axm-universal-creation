import assert from 'node:assert/strict';
import {actionForKey, gamepadActions, InspectionInputRouter} from './inspection_controls.js';

assert.equal(actionForKey({key:' ', target:{tagName:'DIV'}}), 'toggle-play');
assert.equal(actionForKey({key:'2', target:{tagName:'DIV'}}), 'lod-1');
assert.equal(actionForKey({key:'f', target:{tagName:'SELECT'}}), null);
assert.equal(actionForKey({key:'w', ctrlKey:true, target:{tagName:'DIV'}}), null);

const pad = {buttons:Array.from({length:16},()=>({pressed:false})), axes:[0,0]};
pad.buttons[0].pressed=true;
pad.buttons[15].pressed=true;
assert.deepEqual(gamepadActions(pad, Array(16).fill(false)), ['toggle-play','next-clip']);
assert.deepEqual(gamepadActions(pad, pad.buttons.map(button=>button.pressed)), []);

const shoulderPad = {buttons:Array.from({length:16},()=>({pressed:false})), axes:[0,0]};
shoulderPad.buttons[4].pressed=true;
shoulderPad.buttons[12].pressed=true;
assert.deepEqual(gamepadActions(shoulderPad, Array(16).fill(false)), ['lod-previous','view-front']);

const listeners = new Map();
const events=[];
const target={
  addEventListener(type, fn){listeners.set(type, fn);},
  removeEventListener(type){listeners.delete(type);}
};
const router=new InspectionInputRouter({target,navigatorRef:{getGamepads:()=>[]},onAction:(action,mode)=>events.push([action,mode])});
router.start();
let prevented=false;
listeners.get('keydown')({key:'r',target:{tagName:'DIV'},preventDefault(){prevented=true;}});
assert.deepEqual(events,[['restart-clip','keyboard']]);
assert.equal(prevented,true);
router.stop();
assert.equal(listeners.has('keydown'),false);

const gamepadEvents=[];
const axisPad={buttons:Array.from({length:16},()=>({pressed:false})),axes:[0.8,-0.9]};
axisPad.buttons[5].pressed=true;
const gamepadRouter=new InspectionInputRouter({target,navigatorRef:{getGamepads:()=>[axisPad]},onAction:(action,mode)=>gamepadEvents.push([action,mode])});
gamepadRouter.poll();
assert.deepEqual(gamepadEvents,[['lod-next','gamepad'],['orbit-right','gamepad'],['zoom-in','gamepad']]);
console.log('inspection controls: PASS');
