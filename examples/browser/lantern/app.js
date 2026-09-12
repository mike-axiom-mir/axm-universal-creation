// Authored interactive reference. No claim of independent source invention.
const power=document.querySelector('#power');
const intensity=document.querySelector('#intensity');
let lit=false;
function render(){
 document.body.classList.toggle('lit',lit);
 document.body.style.setProperty('--warmth',Number(intensity.value)/100);
 power.setAttribute('aria-pressed',String(lit));
 document.querySelector('#powerLabel').textContent=lit?'Extinguish the lantern':'Light the lantern';
 document.querySelector('#state').textContent=lit?'The lantern is lit. Adjust its glow.':'The lantern is waiting.';
 document.querySelector('#sceneState').textContent=lit?'ILLUMINATED':'UNLIT';
 document.querySelector('#level').textContent=intensity.value+'%';
 intensity.disabled=!lit;
}
power.addEventListener('click',()=>{lit=!lit;render();});
intensity.addEventListener('input',render);
render();
