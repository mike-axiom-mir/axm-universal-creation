"""Reusable dependency-free oblique arena renderer emitted by browser_game.

Geometry, lighting cues and particles are stylized presentation, not a physical
renderer. Gameplay remains in the original world plane; picking inverts it.
"""
ARENA_VISUALS_JS = r'''
const WORLD = SPEC.viewport;
const reduceMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)').matches : false;
const deckTexture = new Image(); deckTexture.src = 'assets/deck.png';
// One disposable realization cache, outside canonical gameplay state.
let deckCache = null;
let deckCacheTextureReady = false;
let deckCacheUnavailable = false;
function shadeColor(color, amount) {
  const channels=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16));
  return '#'+channels.map(c=>Math.round(amount<0?c*(1+amount):c+(255-c)*amount).toString(16).padStart(2,'0')).join('')+color.slice(7);
}
const playerPaint={top:shadeColor(SPEC.player.color,-.18),side:shadeColor(SPEC.player.color,-.40),shadow:shadeColor(SPEC.player.color,-.57),highlight:shadeColor(SPEC.player.color,.25)};
const relayPaint={top:shadeColor(SPEC.tower.color,.25),side:shadeColor(SPEC.tower.color,-.35),shadow:shadeColor(SPEC.tower.color,-.55),highlight:shadeColor(SPEC.tower.color,.45)};
function project(x,y,z=0) {
  return {x:WORLD.width*.5+(x-WORLD.width*.5)*.72-(y-WORLD.height*.5)*.36,
          y:WORLD.height*.52+(x-WORLD.width*.5)*.14+(y-WORLD.height*.5)*.56-z};
}
function unproject(x,y) {
  const dx=x-WORLD.width*.5,dy=y-WORLD.height*.52;
  return {x:WORLD.width*.5+(dx*.56+dy*.36)/.4536,y:WORLD.height*.5+(dy*.72-dx*.14)/.4536};
}
function polygon(points,fill,stroke=null,width=1) {
  ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();
  if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke();}
}
function plane(x,y,w,h,z,fill,stroke=null) {polygon([project(x,y,z),project(x+w,y,z),project(x+w,y+h,z),project(x,y+h,z)],fill,stroke);}
function beam(x1,y1,z1,x2,y2,z2,color,width=1) {const a=project(x1,y1,z1),b=project(x2,y2,z2);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}
function box(x,y,w,h,z,height,top='#647783',left='#263e4b',right='#365463') {
  polygon([project(x,y+h,z),project(x+w,y+h,z),project(x+w,y+h,z+height),project(x,y+h,z+height)],left,'#14242c');
  polygon([project(x+w,y,z),project(x+w,y+h,z),project(x+w,y+h,z+height),project(x+w,y,z+height)],right,'#14242c');
  plane(x,y,w,h,z+height,top,'#819ba044');
}
function disc(x,y,z,r,fill,stroke=null,width=1) {
  const points=[];for(let i=0;i<40;i++){const a=i*Math.PI/20;points.push(project(x+Math.cos(a)*r,y+Math.sin(a)*r,z));}polygon(points,fill,stroke,width);
}
function glow(x,y,z,r,color,opacity=1) {const p=project(x,y,z);ctx.save();ctx.globalAlpha=opacity;const g=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,r);g.addColorStop(0,color);g.addColorStop(1,color.slice(0,7)+'00');ctx.fillStyle=g;ctx.fillRect(p.x-r,p.y-r,r*2,r*2);ctx.restore();}
function shadow(x,y,r) {disc(x+9,y+13,0,r,'#00000066');}
function noise(i){const n=Math.sin(i*127.1+19.19)*43758.5453;return n-Math.floor(n);}
function burst(x,y,color,count=12) {
  if(reduceMotion)return;
  for(let i=0;i<count;i++){const n=state.fxSerial++;const a=noise(n)*Math.PI*2;state.fx.push({x,y,z:12,vx:Math.cos(a)*(30+noise(n+3)*90),vy:Math.sin(a)*(30+noise(n+3)*90),vz:35+noise(n+5)*65,life:.25+noise(n+8)*.4,maxLife:.7,color});}
  if(state.fx.length>180)state.fx.splice(0,state.fx.length-180);
}
function drawDeck() {
  const ready=Boolean(deckTexture.complete && deckTexture.naturalWidth);
  if(deckCache && deckCacheTextureReady===ready && deckCache.width===canvas.width && deckCache.height===canvas.height){
    ctx.drawImage(deckCache,0,0,WORLD.width,WORLD.height);
    return;
  }
  // Paint an opaque static layer first; copy it before any units/effects/HUD.
  drawDeckSurface();
  if(deckCacheUnavailable)return;
  try {
    if(!deckCache)deckCache=document.createElement('canvas');
    deckCache.width=canvas.width;deckCache.height=canvas.height;
    const cacheContext=deckCache.getContext('2d');
    if(!cacheContext)throw new Error('No static-layer canvas context');
    cacheContext.drawImage(canvas,0,0);
    deckCacheTextureReady=ready;
  } catch (_) {
    // Allocation failure keeps direct drawing functional, with no retry storm.
    deckCache=null;deckCacheUnavailable=true;
  }
}
function drawDeckSurface() {
  const W=WORLD.width,H=WORLD.height;
  ctx.fillStyle='#030b12';ctx.fillRect(0,0,W,H);
  const sky=ctx.createLinearGradient(0,0,W,H);sky.addColorStop(0,'#102532');sky.addColorStop(.55,SPEC.theme.background);sky.addColorStop(1,'#030b12');ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);
  for(let i=0;i<75;i++){ctx.fillStyle=i%5===0?'#60808b66':'#63859624';ctx.fillRect(noise(i)*W,noise(i+900)*H,1+(i%3===0),1);}
  // Distant terrain silhouettes, entirely decorative.
  for(let band=0;band<3;band++){const pts=[{x:0,y:H}];for(let x=0;x<=W+40;x+=40)pts.push({x,y:H*.4+band*70-noise(x+band*21)*95});pts.push({x:W,y:H});polygon(pts,['#102a34','#102530','#0b202a'][band]);}
  const corners=[project(0,0,-22),project(W,0,-22),project(W,H,-22),project(0,H,-22)];
  polygon(corners,'#02080ccc');
  box(0,0,W,H,-17,17,SPEC.theme.ground,'#101f29','#1a303b');
  if(deckTexture.complete&&deckTexture.naturalWidth){ctx.save();const p=project(0,0);ctx.transform(.72,.14,-.36,.56,p.x,p.y);ctx.globalAlpha=.4;ctx.fillStyle=ctx.createPattern(deckTexture,'repeat');ctx.fillRect(0,0,W,H);ctx.restore();}
  for(let x=0;x<W;x+=64)for(let y=0;y<H;y+=54){const k=(x*13+y*7);plane(x+2,y+2,Math.min(60,W-x-3),Math.min(50,H-y-3),.2,noise(k)>.55?'#8196a10c':'#0000000c','#b7d7e00b');}
  // Recessed service lanes and two continuous power conduits.
  plane(W*.46,0,W*.08,H,.5,'#101e27');
  plane(0,H*.48,W,H*.1,.5,'#152730');
  for(const x of [W*.45,W*.55]){beam(x,8,1,x,H-8,1,'#0b151a',5);beam(x,8,2,x,H-8,2,SPEC.theme.accent.slice(0,7)+'55',1.3);}
  for(let y=34;y<H;y+=48){plane(W*.485,y, W*.03,3,1,'#bac5bb55');}
  beam(0,0,1,W,0,1,'#8ca6b26b',2);beam(0,H,1,W,H,1,'#526f7c',2);
  beam(W,0,1,W,H,1,'#8ca6b277',2);beam(0,0,1,0,H,1,'#b3d6d366',2);
  for(let x=32;x<W;x+=92){beam(x,H,-8,x+27,H,-8,SPEC.theme.accent.slice(0,7)+'bb',2);}
  // Boundary bollards and service architecture do not create collision walls.
  for(const [x,y] of [[30,32],[W-50,32],[30,H-50],[W-50,H-50]]){
    shadow(x+10,y+10,19);box(x,y,22,22,0,12,'#506570');box(x+5,y+5,12,12,12,28,'#6e8490','#263946','#3d5561');
    disc(x+11,y+11,42,5,SPEC.theme.accent);glow(x+11,y+11,40,22,SPEC.theme.accent.slice(0,7)+'66');
  }
  for(const [x,y] of [[W*.12,H*.8],[W*.8,H*.15]]){
    shadow(x+30,y+16,40);box(x,y,66,35,0,15,'#526874','#2a3f4c','#344c59');
    for(let i=0;i<5;i++)plane(x+8+i*10,y+5,5,25,16,'#182d38');beam(x+4,y+35,10,x+60,y+35,10,'#d8a761',2);
  }
  ctx.textAlign='left';ctx.font='600 10px system-ui';ctx.fillStyle='#94b7c6';ctx.fillText('NORTH RIDGE / RELAY STATION',25,30);
  ctx.font='10px ui-monospace,monospace';ctx.fillStyle='#587987';ctx.fillText('SECTOR 07     •     LOCAL SIGNAL',25,47);
}
function drawRelay() {
  const t=state.tower,cx=t.x+t.width/2,cy=t.y+t.height/2;
  const w=t.width,h=t.height,unit=Math.min(w,h)/105;
  shadow(cx,cy,Math.max(w,h)*.63);
  disc(cx,cy,1,w*.66,'#081d2580',SPEC.theme.accent.slice(0,7)+'55',1);
  box(t.x-9,t.y-9,w+18,h+18,0,9,'#526977','#263945','#344b58');
  box(t.x,t.y,w,h,9,25*unit,relayPaint.top,relayPaint.shadow,relayPaint.side);
  for(let i=0;i<6;i++){beam(t.x+12+i*w*.14,t.y+h,15,t.x+12+i*w*.14,t.y+h,30*unit,'#0b2835',3);}
  box(t.x+w*.12,t.y+h*.12,w*.76,h*.76,9+25*unit,12*unit,relayPaint.highlight,relayPaint.shadow,relayPaint.side);
  // Four structural pylons support a luminous segmented reactor.
  for(const [u,v] of [[.14,.16],[.8,.16],[.14,.76],[.8,.76]])box(t.x+w*u,t.y+h*v,w*.09,h*.09,46*unit,31*unit,'#8ea5ad','#344f5c','#526e7b');
  disc(cx,cy,49*unit,w*.26,'#0d2c38',SPEC.theme.accent,2);
  const pulse=reduceMotion?1: .8+.2*Math.sin(state.time*2.5);
  glow(cx,cy,68*unit,75*unit,SPEC.theme.accent.slice(0,7)+'70',pulse);
  for(let z=52;z<82;z+=8)disc(cx,cy,z*unit,w*.2,null,SPEC.theme.accent.slice(0,7)+(z%16===4?'aa':'55'),1.5);
  disc(cx,cy,82*unit,w*.27,'#426772',SPEC.theme.accent,2);
  disc(cx,cy,84*unit,w*.16,'#b9fff1');
  beam(cx,cy,85*unit,cx,cy,126*unit,'#a0c5cc',2);
  beam(cx-16,cy,110*unit,cx+16,cy,110*unit,'#8aaab4',2);
  glow(cx,cy,128*unit,10,'#bffff0cc');
  const p=project(cx,cy,148*unit);ctx.textAlign='center';ctx.fillStyle='#d6f0ed';ctx.font='600 10px system-ui';ctx.fillText('SIGNAL CORE',p.x,p.y);
  ctx.fillStyle='#162b37';ctx.fillRect(p.x-37,p.y+7,74,3);ctx.fillStyle=SPEC.theme.accent;ctx.fillRect(p.x-37,p.y+7,74*t.health/t.max_health,3);
}
function drawDrone(enemy) {
  const r=enemy.size*.5, x=enemy.x,y=enemy.y;
  shadow(x,y,r*1.5);
  const pace=reduceMotion?0:Math.sin(state.time*9+enemy.size)*3;
  for(const [sx,sy] of [[-1,-1],[1,-1],[-1,1],[1,1]]){
    beam(x+sx*r*.5,y+sy*r*.45,13,x+sx*r*1.2,y+sy*(r+pace),3,'#141b24',6);
    beam(x+sx*r*.5,y+sy*r*.45,14,x+sx*r*1.2,y+sy*(r+pace),4,'#758087',2);
    box(x+sx*r*1.2-4,y+sy*(r+pace)-4,8,8,1,4,'#5b6770','#262e37','#333d46');
  }
  box(x-r,y-r*.65,r*2,r*1.3,11,10,'#725b64','#362c37','#503744');
  box(x-r*.73,y-r*.47,r*1.46,r*.94,21,6,'#b58b91','#58404b','#715260');
  plane(x-r*.58,y-r*.3,r*1.16,r*.19,28,enemy.color);
  beam(x-r*.45,y+r*.66,17,x+r*.45,y+r*.66,17,'#ff777e',2.5);
  glow(x,y,23,enemy.size*.65,enemy.color.slice(0,7)+'45');
  const p=project(x,y,38);ctx.fillStyle='#101e27';ctx.fillRect(p.x-r,p.y,r*2,3);ctx.fillStyle=enemy.color;ctx.fillRect(p.x-r,p.y,r*2*Math.max(0,enemy.health)/enemy.maxHealth,3);
  const target=selectedEnemy();
  if(target?.id===enemy.id){disc(x,y,1,r*1.65,null,'#ffb2a3',1.2);for(const sx of [-1,1])beam(x+sx*r*1.7,y-r,2,x+sx*r*1.7,y+r,2,'#ffb2a3',1.5);}
}
function drawPlayer() {
  const p=state.player,r=p.size,x=p.x,y=p.y,target=selectedEnemy();
  const aim=pointerHeld&&pointerAim?pointerAim:target;
  const a=aim?Math.atan2(aim.y-y,aim.x-x):-Math.PI/2;
  shadow(x,y,r*1.2);
  for(const side of [-1,1]){
    box(x+side*r*.85-r*.18,y-r,r*.36,r*2,1,8,'#465762','#172732','#293c48');
    for(let k=0;k<6;k++)beam(x+side*r*.85-r*.15,y-r+k*r*.34,9,x+side*r*.85+r*.15,y-r+k*r*.34,9,'#80929a',1);
  }
  box(x-r*.6,y-r*.75,r*1.2,r*1.5,7,10,playerPaint.top,playerPaint.shadow,playerPaint.side);
  box(x-r*.42,y-r*.38,r*.84,r*.76,17,8,playerPaint.highlight,playerPaint.side,playerPaint.top);
  const recoil=state.fireCooldown>SPEC.rules.fire_cooldown_ms/1000*.65?4:0;
  beam(x,y,24,x+Math.cos(a)*(r*1.8-recoil),y+Math.sin(a)*(r*1.8-recoil),24,'#263d49',7);
  beam(x,y,26,x+Math.cos(a)*(r*1.8-recoil),y+Math.sin(a)*(r*1.8-recoil),26,'#c4d5d8',3);
  beam(x-r*.3,y+r*.76,14,x+r*.3,y+r*.76,14,SPEC.theme.accent,2);
  if(aim){const d=Math.hypot(aim.x-x,aim.y-y);const ex=x+Math.cos(a)*Math.min(d,110),ey=y+Math.sin(a)*Math.min(d,110);ctx.setLineDash([2,7]);beam(x,y,2,ex,ey,2,'#e9c48b55');ctx.setLineDash([]);}
  if(state.reloadRemaining>0){const p=project(x,y,39);ctx.font='9px system-ui';ctx.textAlign='center';ctx.fillStyle='#f2d39a';ctx.fillText('RELOADING',p.x,p.y);}
}
function draw() {
  const W=WORLD.width,H=WORLD.height;
  ctx.save();ctx.setTransform(renderScale,0,0,renderScale,0,0);
  drawDeck();
  drawConstructionGrid();
  // World depth controls overlap; raised geometry does not change collision coordinates.
  const objects=[{depth:project(state.tower.x+state.tower.width/2,state.tower.y+state.tower.height/2).y,paint:drawRelay},
    {depth:project(state.player.x,state.player.y).y,paint:drawPlayer},
    ...(state.construction?state.construction.buildings.map(b=>({depth:project((b.col+.5)*SPEC.construction.cell_size,(b.row+.5)*SPEC.construction.cell_size).y,paint:()=>drawSupportBuilding(b)})):[]),
    ...state.enemies.filter(e=>e.alive).map(e=>({depth:project(e.x,e.y).y,paint:()=>drawDrone(e)}))];
  objects.sort((a,b)=>a.depth-b.depth).forEach(o=>o.paint());
  for(const b of state.supportBeams){beam(b.x,b.y,26,b.tx,b.ty,21,'#fff0a4',2.5);}
  for(const b of state.bullets){beam(b.x-b.vx*.022,b.y-b.vy*.022,21,b.x,b.y,21,'#80ffe3',3);glow(b.x,b.y,21,10,'#72ffde88');}
  for(const f of state.fx){const p=project(f.x,f.y,f.z);ctx.globalAlpha=Math.max(0,f.life/f.maxLife);ctx.fillStyle=f.color;ctx.fillRect(p.x,p.y,2,2);}ctx.globalAlpha=1;
  // Edge vignette keeps the active play area brighter than the surroundings.
  const vignette=ctx.createRadialGradient(W*.5,H*.5,H*.28,W*.5,H*.5,W*.64);vignette.addColorStop(0,'#00000000');vignette.addColorStop(1,'#02081299');ctx.fillStyle=vignette;ctx.fillRect(0,0,W,H);
  ctx.textAlign='left';ctx.font='600 10px system-ui';ctx.fillStyle='#9db6c3';ctx.fillText('HOSTILES REMAINING',24,H-32);ctx.font='600 18px ui-monospace,monospace';ctx.fillStyle='#e5eeee';ctx.fillText(String(state.enemies.filter(e=>e.alive).length).padStart(2,'0')+' / '+String(state.enemies.length).padStart(2,'0'),24,H-12);
  if(state.phase==='ready'||state.phase==='paused') {ctx.textAlign='right';ctx.font='12px system-ui';ctx.fillStyle='#b6cbd3';ctx.fillText(state.phase==='ready'?'Start the defense when you’re ready.':state.betweenWaves?'Wave cleared — build, then launch when ready.':'Session paused — your tower is safe.',W-24,H-22);}
  if(state.phase==='won'||state.phase==='lost'){ctx.fillStyle='#06121bcb';ctx.fillRect(0,0,W,H);ctx.textAlign='center';ctx.font='600 12px system-ui';ctx.fillStyle=SPEC.theme.accent;ctx.fillText(SPEC.title.toUpperCase()+' / SESSION COMPLETE',W/2,H/2-44);ctx.font='600 40px system-ui';ctx.fillStyle='#e5f3ee';ctx.fillText(state.phase==='won'?'RELAY SECURED':'SIGNAL LOST',W/2,H/2+6);ctx.font='14px system-ui';ctx.fillStyle='#aabcc7';ctx.fillText('Credits earned: '+state.score,W/2,H/2+38);}
  ctx.restore();
}
'''
