"""Optional bounded wave plan; explicit launches reuse the arena session graph."""

def validate_waves(raw):
    from .browser_game import _object,_integer,_number
    w=_object(raw,'waves',{'count','health_step','speed_step','clear_bonus'})
    return {'count':_integer(w['count'],'waves.count',1,12),'health_step':_number(w['health_step'],'health_step',0,1),'speed_step':_number(w['speed_step'],'speed_step',0,1),'clear_bonus':_integer(w['clear_bonus'],'clear_bonus',0,1000000)}


WAVES_JS = r'''
const WaveCycle=(()=>{
  function enemies(base,plan,index){
    if(!Number.isInteger(index)||index<0||index>=(plan?.count||1))throw new Error('Wave index outside plan');
    return base.map(e=>{const health=Math.min(1000000,Math.round(e.health*(1+index*(plan?.health_step||0))));return {...e,health,maxHealth:health,speed:Math.min(1000,e.speed*(1+index*(plan?.speed_step||0))),alive:true,contactCooldown:0};});
  }
  return {enemies};
})();
function completeWave(){
  if(state.phase!=='playing'||state.enemies.some(e=>e.alive))return;
  if(!SPEC.waves){transition('win');return;}
  if(state.wavesCleared>state.waveIndex)return;
  state.wavesCleared=state.waveIndex+1;
  if(state.construction)Construction.reward(state.construction,SPEC.waves.clear_bonus);else state.score+=SPEC.waves.clear_bonus;
  state.bullets=[];state.supportBeams=[];clearInputs();buildKind=null;
  if(state.wavesCleared>=SPEC.waves.count){transition('win');if(SPEC.construction)constructionMessage('Outpost secured. All waves cleared and final bonus received.');return;}
  state.betweenWaves=true;transition('pause');
  if(SPEC.construction)constructionMessage('Wave cleared. Bonus received. Build now, then launch the next wave when ready. Income is paused.');
}
function launchNextWave(){
  if(!SPEC.waves||!state.betweenWaves||state.phase!=='paused')return false;
  state.waveIndex+=1;state.betweenWaves=false;
  state.enemies=WaveCycle.enemies(SPEC.enemies,SPEC.waves,state.waveIndex);
  state.selectedId=state.enemies[0].id;
  state.ammo=SPEC.rules.ammo_capacity;state.reloadRemaining=0;state.fireCooldown=0;
  state.bullets=[];state.fx=[];state.supportBeams=[];constructionClock=0;
  buildKind=null;buildHover=null;clearInputs();
  transition('resume');
  if(SPEC.construction)constructionMessage('Wave '+(state.waveIndex+1)+' underway. Magazine replenished.');
  return true;
}
function updateWaveHud(){
  if(!SPEC.waves)return;
  const label='Wave '+(state.waveIndex+1)+' / '+SPEC.waves.count;
  document.querySelector('#waveValue').textContent=label;
  if(state.betweenWaves){
    statusNode.textContent='Wave cleared — build, then launch when ready.';
    sessionButton.textContent='Launch wave '+(state.waveIndex+2);
  }else if(state.phase==='playing')statusNode.textContent=label+' — defend the core.';
  else if(state.phase==='won')statusNode.textContent='All '+SPEC.waves.count+' waves cleared.';
}
'''
