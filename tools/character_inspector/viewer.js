import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { InspectionInputRouter } from './inspection_controls.js';

const ui = Object.fromEntries(['viewport','clip','prevClip','play','nextClip','restart','scrub','time','lod','lighting','front','back','reset','wire','rig','status','inputStatus','stats','viewState','motionState','inputMode'].map(id=>[id,document.getElementById(id)]));
const params = new URLSearchParams(location.search);
const base = new URL(params.get('asset') || './', location.href);
if (base.origin !== location.origin) throw new Error('Only same-origin local model directories are supported.');
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
ui.viewport.prepend(renderer.domElement);
renderer.domElement.setAttribute('aria-label','OOPS 3D model. Drag to orbit; keyboard and gamepad inspection shortcuts are available.');
renderer.domElement.tabIndex=0;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#172a32');
scene.fog = new THREE.Fog(scene.background,5,12);
const camera = new THREE.PerspectiveCamera(34,1,.02,50);
const controls = new OrbitControls(camera,renderer.domElement);
controls.enableDamping=!matchMedia('(prefers-reduced-motion: reduce)').matches;
controls.minDistance=.35;
controls.maxDistance=10;
controls.target.set(0,.75,0);
camera.position.set(1.6,1.35,2.65);
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
const environment = pmrem.fromScene(room,.04);
scene.environment = environment.texture;
scene.environmentIntensity=.7;
room.dispose();pmrem.dispose();
const key = new THREE.DirectionalLight(0xffe5cc,3.2);
key.position.set(-2,4,3);key.castShadow=true;
key.shadow.mapSize.set(2048,2048);key.shadow.camera.left=-2;key.shadow.camera.right=2;
key.shadow.camera.top=2;key.shadow.camera.bottom=-2;key.shadow.normalBias=.003;
scene.add(key);
const fill = new THREE.DirectionalLight(0xa1e0ff,1.4);fill.position.set(3,2,-2);scene.add(fill);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:0x203941,roughness:.9}));
ground.rotation.x=-Math.PI/2;ground.position.y=-.001;ground.receiveShadow=true;scene.add(ground);
let model, mixer, clips=[], action, skeleton, playing=false, generation=0, last=performance.now(), currentView='three-quarter';

function resize(){const {width,height}=ui.viewport.getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(ui.viewport);

function setInputMode(mode){ui.inputMode.textContent=`INPUT · ${mode.toUpperCase()}`;}
function feedback(message){ui.inputStatus.textContent=message;}
function syncMotionState(){
  if(!action){ui.motionState.textContent='MOTION · BIND';return;}
  ui.motionState.textContent=`MOTION · ${playing?'PLAY':'PAUSE'} · ${action.getClip().name}`;
}
function syncViewState(){ui.viewState.textContent=`VIEW · ${currentView==='three-quarter'?'3/4':currentView.toUpperCase()}`;}
function setClip(name){
  if(!mixer||!model)return;
  mixer.stopAllAction();action=null;
  model.traverse(node=>{if(node.isSkinnedMesh)node.skeleton.pose();});
  const clip=clips.find(clip=>clip.name===name);
  if(clip){action=mixer.clipAction(clip);action.reset().play();action.setLoop(THREE.LoopRepeat,Infinity);mixer.update(0);}
  playing=false;ui.play.textContent='Play';ui.scrub.value=0;ui.time.textContent='0.000 s';syncMotionState();
}
function cycleClip(delta){
  if(!ui.clip.options.length)return;
  const next=(ui.clip.selectedIndex+delta+ui.clip.options.length)%ui.clip.options.length;
  ui.clip.selectedIndex=next;setClip(ui.clip.value);feedback(`Animation: ${ui.clip.selectedOptions[0]?.text || 'Bind pose'}`);
}
function restartClip(){if(action){action.reset().play();mixer.update(0);ui.scrub.value=0;ui.time.textContent='0.000 s';feedback(`Restarted ${action.getClip().name}`);}else feedback('Bind pose has no timeline to restart.');}
function togglePlay(){
  if(!action){feedback('Choose an animation clip first.');return;}
  playing=!playing;ui.play.textContent=playing?'Pause':'Play';syncMotionState();feedback(`${playing?'Playing':'Paused'} ${action.getClip().name}`);
}
function cycleLod(delta){const next=(Number(ui.lod.value)+delta+3)%3;ui.lod.value=String(next);load();feedback(`Loading LOD ${next}.`);}

function fitView(name=currentView){
  if(!model)return;
  model.updateMatrixWorld?.(true);
  const box=new THREE.Box3().setFromObject(model);
  if(box.isEmpty())return;
  const center=box.getCenter(new THREE.Vector3());
  const size=box.getSize(new THREE.Vector3());
  const radius=Math.max(size.length()*.5,.12);
  const vertical=THREE.MathUtils.degToRad(camera.fov*.5);
  const horizontal=Math.atan(Math.tan(vertical)*Math.max(camera.aspect,.25));
  const limiting=Math.max(.12,Math.min(vertical,horizontal));
  const distance=Math.min(controls.maxDistance,Math.max(controls.minDistance,radius/Math.sin(limiting)*1.12));
  const direction={
    front:new THREE.Vector3(0,.03,1),
    back:new THREE.Vector3(0,.03,-1),
    'three-quarter':new THREE.Vector3(.62,.12,1)
  }[name] || new THREE.Vector3(.62,.12,1);
  direction.normalize();controls.target.copy(center);camera.position.copy(center).addScaledVector(direction,distance);
  camera.near=Math.max(.01,distance-radius*3);camera.far=Math.max(50,distance+radius*5);camera.updateProjectionMatrix();controls.update();
  currentView=name;syncViewState();feedback(`${name==='three-quarter'?'3/4':name} view · auto-framed to exported bounds`);
}
function stepOrbit(direction){
  if(!model)return;
  const offset=camera.position.clone().sub(controls.target);
  offset.applyAxisAngle(new THREE.Vector3(0,1,0),direction*Math.PI/12);
  camera.position.copy(controls.target).add(offset);controls.update();
  currentView='free';syncViewState();feedback(`Orbit step ${direction>0?'left':'right'}.`);
}
function stepZoom(direction){
  if(!model)return;
  const offset=camera.position.clone().sub(controls.target);
  const distance=offset.length();
  const next=Math.min(controls.maxDistance,Math.max(controls.minDistance,distance*(direction>0?.88:1.14)));
  if(distance>0)offset.setLength(next);
  camera.position.copy(controls.target).add(offset);controls.update();currentView='free';syncViewState();feedback(direction>0?'Zoomed in.':'Zoomed out.');
}
function toggleCheckbox(control,label){control.checked=!control.checked;control.dispatchEvent(new Event('change'));feedback(`${label}: ${control.checked?'on':'off'}`);}
function performAction(actionName,source){
  setInputMode(source);
  switch(actionName){
    case 'toggle-play': togglePlay(); break;
    case 'restart-clip': restartClip(); break;
    case 'previous-clip': cycleClip(-1); break;
    case 'next-clip': cycleClip(1); break;
    case 'lod-0': case 'lod-1': case 'lod-2': ui.lod.value=actionName.slice(-1);load();feedback(`Loading LOD ${ui.lod.value}.`);break;
    case 'lod-previous': cycleLod(-1); break;
    case 'lod-next': cycleLod(1); break;
    case 'view-front': fitView('front'); break;
    case 'view-back': fitView('back'); break;
    case 'view-three-quarter': fitView('three-quarter'); break;
    case 'orbit-left': stepOrbit(1); break;
    case 'orbit-right': stepOrbit(-1); break;
    case 'zoom-in': stepZoom(1); break;
    case 'zoom-out': stepZoom(-1); break;
    case 'toggle-wireframe': toggleCheckbox(ui.wire,'Wireframe'); break;
    case 'toggle-skeleton': toggleCheckbox(ui.rig,'Skeleton'); break;
  }
}

function disposeModel(){
  if(!model)return;
  mixer?.stopAllAction();mixer?.uncacheRoot(model);scene.remove(model);
  const materials=new Set(),textures=new Set();
  model.traverse(node=>{node.geometry?.dispose();for(const mat of Array.isArray(node.material)?node.material:[node.material])if(mat)materials.add(mat);});
  for(const mat of materials){for(const value of Object.values(mat))if(value?.isTexture)textures.add(value);mat.dispose();}
  for(const texture of textures){texture.dispose();texture.image?.close?.();}
  if(skeleton){scene.remove(skeleton);skeleton.dispose();}
}
async function load(){
  const token=++generation;ui.status.textContent='Loading exported GLB…';ui.lod.disabled=true;
  try{
    const url=new URL(`AXM_OOPS_LOD${ui.lod.value}.glb`,base);
    const result=await new GLTFLoader().loadAsync(url.href);
    if(token!==generation)return;
    const selected=ui.clip.value;
    disposeModel();model=result.scene;scene.add(model);clips=result.animations;mixer=new THREE.AnimationMixer(model);
    let triangles=0,vertices=0,bones=0,materials=new Set(),maps=new Set();
    model.traverse(node=>{
      if(node.isBone)bones++;
      if(!node.isMesh)return;
      node.castShadow=true;node.receiveShadow=true;node.frustumCulled=false;
      triangles+=(node.geometry.index?.count || node.geometry.attributes.position.count)/3;
      vertices+=node.geometry.attributes.position.count;
      for(const mat of Array.isArray(node.material)?node.material:[node.material]){
        materials.add(mat);mat.wireframe=ui.wire.checked;
        for(const role of ['map','normalMap','roughnessMap','metalnessMap','aoMap'])if(mat[role])maps.add(`${mat[role].image.width} × ${mat[role].image.height}`);
      }
    });
    skeleton=new THREE.SkeletonHelper(model);skeleton.visible=ui.rig.checked;scene.add(skeleton);
    ui.clip.replaceChildren(new Option('Bind pose',''),...clips.map(clip=>new Option(clip.name,clip.name)));
    ui.clip.value=clips.some(clip=>clip.name===selected)?selected:'';
    setClip(ui.clip.value);fitView(currentView==='free'?'three-quarter':currentView);
    ui.stats.textContent=`${Math.round(triangles).toLocaleString()} triangles\n${vertices.toLocaleString()} exported vertices\n${bones} bones · ${materials.size} material\n${clips.length} animation clips\nMaps: ${[...maps].join(', ')}\nLoaded: ${url.pathname.split('/').slice(-2).join('/')}`;
    ui.status.textContent='Export loaded · ready to inspect';
  }catch(error){ui.status.textContent=`Model load failed: ${error.message}`;console.error(error);}
  finally{ui.lod.disabled=false;}
}
ui.clip.addEventListener('change',()=>{setClip(ui.clip.value);feedback(`Animation: ${ui.clip.selectedOptions[0]?.text || 'Bind pose'}`);});
ui.prevClip.addEventListener('click',()=>cycleClip(-1));ui.nextClip.addEventListener('click',()=>cycleClip(1));
ui.play.addEventListener('click',togglePlay);ui.restart.addEventListener('click',restartClip);
ui.scrub.addEventListener('input',()=>{if(!action)return;playing=false;ui.play.textContent='Play';action.time=Number(ui.scrub.value)*action.getClip().duration;mixer.update(0);syncMotionState();feedback(`Pose at ${action.time.toFixed(3)} seconds.`);});
ui.lod.addEventListener('change',()=>{load();feedback(`Loading LOD ${ui.lod.value}.`);});
ui.wire.addEventListener('change',()=>model?.traverse(node=>{for(const mat of Array.isArray(node.material)?node.material:[node.material])if(mat)mat.wireframe=ui.wire.checked;}));
ui.rig.addEventListener('change',()=>{if(skeleton)skeleton.visible=ui.rig.checked;});
ui.lighting.addEventListener('change',()=>{const neutral=ui.lighting.value==='neutral';scene.background.set(neutral?'#777b7c':'#172a32');scene.fog.color.copy(scene.background);ground.material.color.set(neutral?'#777b7c':'#203941');key.color.set(neutral?0xffffff:0xffe5cc);fill.color.set(neutral?0xffffff:0xa1e0ff);scene.environmentIntensity=neutral?1:.7;key.intensity=neutral?2:3.2;feedback(`${neutral?'Neutral':'Workshop'} lighting.`);});
ui.front.addEventListener('click',()=>fitView('front'));ui.back.addEventListener('click',()=>fitView('back'));ui.reset.addEventListener('click',()=>fitView('three-quarter'));
renderer.domElement.addEventListener('pointerdown',()=>setInputMode('pointer'));
renderer.domElement.addEventListener('wheel',()=>setInputMode('pointer'),{passive:true});
new InspectionInputRouter({onAction:performAction,onInputMode:setInputMode}).start();

renderer.setAnimationLoop(now=>{
  const delta=Math.min((now-last)/1000,.05);last=now;
  if(playing&&mixer)mixer.update(delta);
  if(action){ui.time.textContent=`${action.time.toFixed(3)} s`;if(playing)ui.scrub.value=action.time/action.getClip().duration;}
  controls.update();renderer.render(scene,camera);
});
load();
