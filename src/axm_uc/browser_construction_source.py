"""Pure construction operations plus a bounded browser-arena adapter."""
CONSTRUCTION_JS = r'''
const Construction=(()=>{
  const LIMIT=1000000000;
  function create(spec){return {credits:spec.initial_credits,buildings:[],ticks:0};}
  function canPlace(spec,state,kind,col,row){
    if(!Object.hasOwn(spec.catalog,kind))return {ok:false,reason:'Choose a building.'};
    if(!Number.isInteger(col)||!Number.isInteger(row)||col<0||row<0||col>=spec.cols||row>=spec.rows)return {ok:false,reason:'Choose a cell on the deck.'};
    if(spec.blocked.some(c=>c[0]===col&&c[1]===row))return {ok:false,reason:'Reserved cell — choose another.'};
    if(state.buildings.some(b=>b.col===col&&b.row===row))return {ok:false,reason:'That cell is occupied.'};
    if(state.credits<spec.catalog[kind].cost)return {ok:false,reason:'Not enough credits.'};
    return {ok:true,reason:'Ready to place.'};
  }
  function place(spec,state,kind,col,row){
    const result=canPlace(spec,state,kind,col,row);if(!result.ok)return result;
    state.credits-=spec.catalog[kind].cost;
    state.buildings.push({id:state.buildings.length+1,kind,col,row});return result;
  }
  function tick(spec,state,count=1){
    if(!Number.isInteger(count)||count<0||count>3600)throw new Error('Tick count must be 0..3600');
    const income=state.buildings.filter(b=>b.kind==='generator').length*spec.catalog.generator.rate*count;
    state.credits=Math.min(LIMIT,state.credits+income);state.ticks+=count;
    return {income};
  }
  function reward(state,amount){if(!Number.isInteger(amount)||amount<0)throw new Error('Invalid reward');state.credits=Math.min(LIMIT,state.credits+amount);}
  return {create,canPlace,place,tick,reward};
})();
'''

CONSTRUCTION_UI_JS = r'''
let buildKind=null,buildHover=null,constructionClock=0;
function resetConstructionUI(){buildKind=null;buildHover=null;constructionClock=0;if(SPEC.construction)constructionMessage('Place support buildings, then press Start. Income and support run only while playing.');}
function updateConstructionHud(){
  if(!state.construction)return;
  const c=SPEC.construction;
  document.querySelector('#constructionBalance').textContent=state.construction.credits;
  document.querySelector('#constructionIncome').textContent=state.construction.buildings.filter(b=>b.kind==='generator').length*c.catalog.generator.rate;
  document.querySelector('#constructionCount').textContent=state.construction.buildings.length;
  for(const b of document.querySelectorAll('[data-build]')){
    b.setAttribute('aria-pressed',String(buildKind===b.dataset.build));
    b.disabled=['won','lost'].includes(state.phase);
  }
  document.querySelector('#cancelBuild').disabled=!buildKind;
}
function constructionMessage(text){document.querySelector('#buildMessage').textContent=text;}
function placementCheck(kind,col,row){
  const c=SPEC.construction,result=Construction.canPlace(c,state.construction,kind,col,row);
  if(!result.ok)return result;
  const x=col*c.cell_size,y=row*c.cell_size;
  if([state.player,...state.enemies.filter(e=>e.alive)].some(u=>u.x+u.size/2>x&&u.x-u.size/2<x+c.cell_size&&u.y+u.size/2>y&&u.y-u.size/2<y+c.cell_size))return {ok:false,reason:'A unit occupies that cell.'};
  return result;
}
function attemptConstruction(event){
  if(!SPEC.construction||!buildKind)return false;
  if(!['ready','paused','playing'].includes(state.phase))return true;
  const rect=canvas.getBoundingClientRect(),p=unproject((event.clientX-rect.left)*SPEC.viewport.width/rect.width,(event.clientY-rect.top)*SPEC.viewport.height/rect.height);
  const c=SPEC.construction,col=Math.floor(p.x/c.cell_size),row=Math.floor(p.y/c.cell_size);
  const check=placementCheck(buildKind,col,row);
  const result=check.ok?Construction.place(c,state.construction,buildKind,col,row):check;
  constructionMessage(result.ok?c.catalog[buildKind].label+' placed. Choose another cell or Return to combat.':result.reason);
  updateConstructionHud();return true;
}
function applyEnemyDamage(enemy,damage){
  enemy.health-=damage;burst(enemy.x,enemy.y,enemy.color,10);
  if(enemy.health<=0){enemy.alive=false;state.score+=enemy.reward;if(state.construction)Construction.reward(state.construction,enemy.reward);burst(enemy.x,enemy.y,'#ffcd83',24);}
}
function updateConstruction(dt){
  if(!state.construction)return;
  state.supportBeams=state.supportBeams.filter(b=>(b.life-=dt)>0);
  constructionClock+=dt;
  const ticks=Math.floor(constructionClock+1e-9);if(!ticks)return;
  constructionClock-=ticks;
  const c=SPEC.construction;Construction.tick(c,state.construction,ticks);
  for(const b of state.construction.buildings){
    const rule=c.catalog[b.kind],x=(b.col+.5)*c.cell_size,y=(b.row+.5)*c.cell_size;
    if(b.kind==='repair'&&state.tower.health>0&&Math.hypot(x-(state.tower.x+state.tower.width/2),y-(state.tower.y+state.tower.height/2))<=rule.range){state.tower.health=Math.min(state.tower.max_health,state.tower.health+rule.rate*ticks);}
    if(b.kind==='turret'){
      const target=state.enemies.filter(e=>e.alive&&Math.hypot(e.x-x,e.y-y)<=rule.range).sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0];
      if(target){applyEnemyDamage(target,rule.rate*ticks);state.supportBeams.push({x,y,tx:target.x,ty:target.y,life:.18});}
    }
  }
}
function drawConstructionGrid(){
  if(!state.construction||!buildKind)return;
  const c=SPEC.construction,s=c.cell_size;
  for(let col=0;col<c.cols;col++)for(let row=0;row<c.rows;row++){
    const allowed=placementCheck(buildKind,col,row).ok;
    plane(col*s+2,row*s+2,s-4,s-4,2,allowed?'#70d9b512':'#ef69701c',allowed?'#8bdfc052':'#db767544');
  }
}
function drawSupportBuilding(b){
  const s=SPEC.construction.cell_size,x=(b.col+.5)*s,y=(b.row+.5)*s,r=s*.3;
  if(buildKind&&b.kind!=='generator')disc(x,y,2,SPEC.construction.catalog[b.kind].range,null,'#a7d9cd33',1);
  const paint={generator:'#dbb768',turret:'#92b4c5',repair:'#7fd6b9'}[b.kind];
  shadow(x,y,r*1.4);box(x-r,y-r,r*2,r*2,1,9,'#597480','#1d3440','#314b58');
  if(b.kind==='generator'){
    box(x-r*.6,y-r*.6,r*1.2,r*1.2,10,22,paint,'#6b5939','#99804e');
    for(let z=15;z<=30;z+=7)disc(x,y,z,r*.65,null,'#ffe1a0',1.5);
    glow(x,y,31,19,'#e8c16d44');
  }else if(b.kind==='turret'){
    const target=state.enemies.filter(e=>e.alive).sort((a,b)=>Math.hypot(a.x-x,a.y-y)-Math.hypot(b.x-x,b.y-y))[0];
    const angle=target?Math.atan2(target.y-y,target.x-x):-Math.PI/2;
    box(x-r*.6,y-r*.6,r*1.2,r*1.2,10,13,paint,'#35505e','#5b7c8a');
    beam(x,y,25,x+Math.cos(angle)*r*1.5,y+Math.sin(angle)*r*1.5,25,'#243d4b',8);beam(x,y,27,x+Math.cos(angle)*r*1.5,y+Math.sin(angle)*r*1.5,27,'#c2d4d6',3);
  }else{
    box(x-r*.75,y-r*.65,r*1.5,r*1.3,10,12,paint,'#2f6357','#529782');
    plane(x-3,y-r*.45,6,r*.9,23,'#e1fff4');plane(x-r*.45,y-3,r*.9,6,23,'#e1fff4');
  }
  const p=project(x,y,44);ctx.textAlign='center';ctx.font='8px system-ui';ctx.fillStyle=paint;ctx.fillText(SPEC.construction.catalog[b.kind].label.toUpperCase(),p.x,p.y);
}
if(SPEC.construction){
  for(const button of document.querySelectorAll('[data-build]'))button.addEventListener('click',()=>{clearInputs();buildKind=button.dataset.build;constructionMessage('Tap a green grid cell to place '+SPEC.construction.catalog[buildKind].label+'.');updateConstructionHud();});
  document.querySelector('#cancelBuild').addEventListener('click',()=>{buildKind=null;constructionMessage('Combat controls active. Income and support run while playing.');updateConstructionHud();canvas.focus({preventScroll:true});});
}
'''
