"use strict";
const SPEC = Object.freeze({"enemies":[{"color":"#FF365E","damage":18,"health":120,"id":"hostile-parent","label":"Hostile Parent","reward":500,"size":42,"speed":24,"x":480,"y":105},{"color":"#F05D7A","damage":8,"health":50,"id":"scout-left","label":"Left Scout","reward":100,"size":28,"speed":34,"x":180,"y":170},{"color":"#F05D7A","damage":8,"health":50,"id":"scout-right","label":"Right Scout","reward":100,"size":28,"speed":34,"x":780,"y":170}],"id":"command-tower-arena","player":{"color":"#FFC857","max_health":100,"size":18,"speed":250,"x":480,"y":450},"rules":{"ammo_capacity":30,"contact_distance":72,"fire_cooldown_ms":180,"projectile_damage":25,"projectile_speed":620,"reload_ms":1400},"schema":"axm.browser-arena/v0.1","theme":{"accent":"#37E4D5","background":"#05090F","danger":"#FF365E","ground":"#12383B","panel":"#07151A","text":"#F4F7F8"},"title":"Command Tower: Hostile Parent","tower":{"color":"#19A7A1","height":105,"max_health":300,"width":150,"x":405,"y":245},"viewport":{"height":540,"width":960}});
const SESSION = Object.freeze({"id":"command-tower-arena.session","initial_state":"ready","schema":"axm.deterministic-state-machine/v0.1","states":["ready","playing","paused","won","lost"],"transitions":[{"effects":[{"type":"reset-session"}],"event":"reset","from":"lost","to":"ready"},{"effects":[{"type":"reset-session"}],"event":"reset","from":"paused","to":"ready"},{"effects":[],"event":"resume","from":"paused","to":"playing"},{"effects":[{"type":"freeze-arena"}],"event":"lose","from":"playing","to":"lost"},{"effects":[],"event":"pause","from":"playing","to":"paused"},{"effects":[{"type":"reset-session"}],"event":"reset","from":"playing","to":"ready"},{"effects":[{"type":"freeze-arena"}],"event":"win","from":"playing","to":"won"},{"effects":[{"type":"begin-session"}],"event":"start","from":"ready","to":"playing"},{"effects":[{"type":"reset-session"}],"event":"reset","from":"won","to":"ready"}]});
const SPEC_DIGEST = "9f71028a271c43801d212dc557fe878cf1607dd174ce627008e4f2425abbf95f";
const SESSION_DIGEST = "582d7ff32aecfe2893dcaee6c83d6533af50b0c1b699bf32fc1e83e107c1573e";
const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const statusNode = document.querySelector("#status");
const sessionButton = document.querySelector("#sessionButton");
const reloadButton = document.querySelector("#reloadButton");
const resetButton = document.querySelector("#resetButton");
const targetName = document.querySelector("#targetName");
const targetHealth = document.querySelector("#targetHealth");
const towerValue = document.querySelector("#towerValue");
const scoreValue = document.querySelector("#scoreValue");
const ammoValue = document.querySelector("#ammoValue");
const fireSound = new Audio("assets/fire.wav");
const keys = new Set();
let state;
let lastFrame = 0;

function transition(event) {
  const row = SESSION.transitions.find(item => item.from === state.phase && item.event === event);
  if (!row) return false;
  state.phase = row.to;
  return true;
}

function freshState() {
  return {
    phase: SESSION.initial_state,
    player: {...SPEC.player, health: SPEC.player.max_health},
    tower: {...SPEC.tower, health: SPEC.tower.max_health},
    enemies: SPEC.enemies.map(enemy => ({...enemy, maxHealth: enemy.health, alive: true, contactCooldown: 0})),
    bullets: [], ammo: SPEC.rules.ammo_capacity, reloadRemaining: 0,
    fireCooldown: 0, score: 0, selectedId: SPEC.enemies[0].id,
  };
}

function reset() {
  state = freshState();
  lastFrame = 0;
  updateHud();
  draw();
}

function selectedEnemy() {
  return state.enemies.find(enemy => enemy.id === state.selectedId && enemy.alive)
    || state.enemies.find(enemy => enemy.alive) || null;
}

function setStatus() {
  const labels = {ready:"Ready — start when you choose.",playing:"Defend the command tower.",paused:"Paused.",won:"Arena secured.",lost:"Command tower lost."};
  statusNode.textContent = labels[state.phase];
  sessionButton.textContent = state.phase === "ready" ? "Start" : state.phase === "playing" ? "Pause" : state.phase === "paused" ? "Resume" : "Play again";
}

function updateHud() {
  const target = selectedEnemy();
  targetName.textContent = target ? target.label : "No hostiles";
  targetHealth.max = target ? target.maxHealth : 1;
  targetHealth.value = target ? Math.max(0, target.health) : 0;
  towerValue.textContent = `${Math.ceil(100 * state.tower.health / state.tower.max_health)}%`;
  scoreValue.textContent = String(state.score);
  ammoValue.textContent = state.reloadRemaining > 0 ? "RELOADING" : `${state.ammo} / ${SPEC.rules.ammo_capacity}`;
  setStatus();
}

function startReload() {
  if (state.phase === "playing" && state.reloadRemaining <= 0 && state.ammo < SPEC.rules.ammo_capacity) {
    state.reloadRemaining = SPEC.rules.reload_ms / 1000;
  }
}

function fireAt(x, y) {
  if (state.phase !== "playing" || state.fireCooldown > 0 || state.reloadRemaining > 0) return;
  if (state.ammo <= 0) { startReload(); return; }
  const dx = x - state.player.x;
  const dy = y - state.player.y;
  const length = Math.hypot(dx, dy) || 1;
  state.bullets.push({x:state.player.x,y:state.player.y,vx:dx/length*SPEC.rules.projectile_speed,vy:dy/length*SPEC.rules.projectile_speed,r:4});
  state.ammo -= 1;
  state.fireCooldown = SPEC.rules.fire_cooldown_ms / 1000;
  try { const cue = fireSound.cloneNode(); cue.volume = 0.25; void cue.play(); } catch (_) { /* audio permission is host-controlled */ }
  if (state.ammo === 0) startReload();
}

function update(dt) {
  if (state.phase !== "playing") return;
  let dx = (keys.has("ArrowRight") || keys.has("d") ? 1 : 0) - (keys.has("ArrowLeft") || keys.has("a") ? 1 : 0);
  let dy = (keys.has("ArrowDown") || keys.has("s") ? 1 : 0) - (keys.has("ArrowUp") || keys.has("w") ? 1 : 0);
  const movement = Math.hypot(dx, dy) || 1;
  state.player.x = Math.max(state.player.size, Math.min(canvas.width-state.player.size, state.player.x + dx/movement*state.player.speed*dt));
  state.player.y = Math.max(state.player.size, Math.min(canvas.height-state.player.size, state.player.y + dy/movement*state.player.speed*dt));
  state.fireCooldown = Math.max(0, state.fireCooldown - dt);
  if (state.reloadRemaining > 0) {
    state.reloadRemaining -= dt;
    if (state.reloadRemaining <= 0) { state.reloadRemaining = 0; state.ammo = SPEC.rules.ammo_capacity; }
  }
  const tx = state.tower.x + state.tower.width / 2;
  const ty = state.tower.y + state.tower.height / 2;
  for (const enemy of state.enemies) {
    if (!enemy.alive) continue;
    const ex = tx - enemy.x;
    const ey = ty - enemy.y;
    const distance = Math.hypot(ex, ey) || 1;
    enemy.contactCooldown = Math.max(0, enemy.contactCooldown - dt);
    if (distance > SPEC.rules.contact_distance) {
      enemy.x += ex / distance * enemy.speed * dt;
      enemy.y += ey / distance * enemy.speed * dt;
    } else if (enemy.contactCooldown <= 0) {
      state.tower.health = Math.max(0, state.tower.health - enemy.damage);
      enemy.contactCooldown = 0.75;
    }
  }
  for (const bullet of state.bullets) { bullet.x += bullet.vx*dt; bullet.y += bullet.vy*dt; }
  for (const bullet of state.bullets) {
    for (const enemy of state.enemies) {
      if (!enemy.alive || bullet.hit || Math.hypot(bullet.x-enemy.x,bullet.y-enemy.y) > enemy.size/2+bullet.r) continue;
      bullet.hit = true;
      enemy.health -= SPEC.rules.projectile_damage;
      if (enemy.health <= 0) { enemy.alive = false; state.score += enemy.reward; }
      break;
    }
  }
  state.bullets = state.bullets.filter(b => !b.hit && b.x>=0 && b.x<=canvas.width && b.y>=0 && b.y<=canvas.height);
  if (state.tower.health <= 0) transition("lose");
  else if (!state.enemies.some(enemy => enemy.alive)) transition("win");
  updateHud();
}

function drawBlock(x,y,size,color) {
  ctx.fillStyle = color; ctx.fillRect(x-size/2,y-size/2,size,size);
  ctx.fillStyle = "rgba(255,255,255,.22)"; ctx.fillRect(x-size*.28,y-size*.28,size*.2,size*.2);
}

function draw() {
  const {width,height} = canvas;
  ctx.fillStyle = SPEC.theme.background; ctx.fillRect(0,0,width,height);
  ctx.strokeStyle = "rgba(59,232,218,.08)"; ctx.lineWidth = 1;
  for (let x=0;x<width;x+=48){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke();}
  for (let y=0;y<height;y+=48){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke();}
  ctx.fillStyle = SPEC.theme.ground;
  ctx.beginPath(); ctx.moveTo(width*.12,height); ctx.lineTo(width*.36,height*.38); ctx.lineTo(width*.66,height*.38); ctx.lineTo(width*.9,height); ctx.closePath(); ctx.fill();
  ctx.fillStyle = state.tower.color; ctx.fillRect(state.tower.x,state.tower.y,state.tower.width,state.tower.height);
  ctx.fillStyle = SPEC.theme.accent; ctx.fillRect(state.tower.x+state.tower.width*.2,state.tower.y-18,state.tower.width*.6,18);
  const target = selectedEnemy();
  for (const enemy of state.enemies) {
    if (!enemy.alive) continue;
    drawBlock(enemy.x,enemy.y,enemy.size,enemy.color);
    ctx.fillStyle = SPEC.theme.danger; ctx.fillRect(enemy.x-enemy.size/2,enemy.y-enemy.size*.78,enemy.size*Math.max(0,enemy.health)/enemy.maxHealth,4);
    if (target && enemy.id === target.id) { ctx.strokeStyle=SPEC.theme.accent;ctx.lineWidth=2;ctx.strokeRect(enemy.x-enemy.size*.72,enemy.y-enemy.size*.72,enemy.size*1.44,enemy.size*1.44); }
  }
  ctx.save(); ctx.translate(state.player.x,state.player.y); ctx.fillStyle=state.player.color; ctx.beginPath(); ctx.moveTo(0,-state.player.size);ctx.lineTo(state.player.size*.75,state.player.size);ctx.lineTo(-state.player.size*.75,state.player.size);ctx.closePath();ctx.fill();ctx.restore();
  ctx.fillStyle = SPEC.theme.accent; for(const bullet of state.bullets){ctx.beginPath();ctx.arc(bullet.x,bullet.y,bullet.r,0,Math.PI*2);ctx.fill();}
  if (state.phase === "won" || state.phase === "lost") { ctx.fillStyle="rgba(0,0,0,.6)";ctx.fillRect(0,0,width,height);ctx.fillStyle=SPEC.theme.text;ctx.textAlign="center";ctx.font="900 48px system-ui";ctx.fillText(state.phase === "won" ? "ARENA SECURED" : "TOWER LOST",width/2,height/2); }
}

function frame(timestamp) {
  const dt = lastFrame ? Math.min((timestamp-lastFrame)/1000,0.05) : 0;
  lastFrame = timestamp;
  update(dt); draw(); requestAnimationFrame(frame);
}

canvas.addEventListener("pointerdown", event => {
  const rect=canvas.getBoundingClientRect(); const x=(event.clientX-rect.left)*canvas.width/rect.width; const y=(event.clientY-rect.top)*canvas.height/rect.height;
  const nearest=state.enemies.filter(e=>e.alive).sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0];
  if (nearest) state.selectedId=nearest.id;
  fireAt(x,y); canvas.focus();
});
window.addEventListener("keydown", event => { const key=event.key.length===1?event.key.toLowerCase():event.key; keys.add(key); if(["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"," "].includes(key))event.preventDefault(); if(key==="p"){if(state.phase==="playing")transition("pause");else if(state.phase==="paused")transition("resume");} if(key==="r")startReload(); });
window.addEventListener("keyup", event => keys.delete(event.key.length===1?event.key.toLowerCase():event.key));
for(const button of document.querySelectorAll("[data-key]")){const key=button.dataset.key;button.addEventListener("pointerdown",()=>keys.add(key));for(const name of ["pointerup","pointercancel","pointerleave"])button.addEventListener(name,()=>keys.delete(key));}
sessionButton.addEventListener("click",()=>{if(state.phase==="ready")transition("start");else if(state.phase==="playing")transition("pause");else if(state.phase==="paused")transition("resume");else{reset();transition("start");}updateHud();canvas.focus();});
reloadButton.addEventListener("click",startReload);
resetButton.addEventListener("click",()=>{if(state.phase!=="ready")transition("reset");reset();});
reset(); requestAnimationFrame(frame);
console.info("AXM browser arena source", {specDigest:SPEC_DIGEST,sessionDigest:SESSION_DIGEST,browserExecutionObserved:false});
