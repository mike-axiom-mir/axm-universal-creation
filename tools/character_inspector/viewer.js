import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const ui = Object.fromEntries(['viewport','clip','play','restart','scrub','time','lod','lighting','front','back','reset','wire','rig','status','stats'].map(id=>[id,document.getElementById(id)]));
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
renderer.domElement.setAttribute('aria-label','OOPS 3D model');
const scene = new THREE.Scene();
scene.background = new THREE.Color('#172a32');
scene.fog = new THREE.Fog(scene.background,5,12);
const camera = new THREE.PerspectiveCamera(34,1,.02,50);
const controls = new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;
controls.minDistance=.35;
controls.maxDistance=6;
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
let model, mixer, clips=[], action, skeleton, playing=false, generation=0, last=performance.now();
function resize(){const {width,height}=ui.viewport.getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(ui.viewport);
function disposeModel(){
  if(!model)return;
  mixer?.stopAllAction();mixer?.uncacheRoot(model);scene.remove(model);
  const materials=new Set(),textures=new Set();
  model.traverse(node=>{node.geometry?.dispose();for(const mat of Array.isArray(node.material)?node.material:[node.material])if(mat)materials.add(mat);});
  for(const mat of materials){for(const value of Object.values(mat))if(value?.isTexture)textures.add(value);mat.dispose();}
  for(const texture of textures){texture.dispose();texture.image?.close?.();}
  if(skeleton){scene.remove(skeleton);skeleton.dispose();}
}
function setClip(name){
  mixer.stopAllAction();action=null;
  model.traverse(node=>{if(node.isSkinnedMesh)node.skeleton.pose();});
  const clip=clips.find(clip=>clip.name===name);
  if(clip){action=mixer.clipAction(clip);action.reset().play();action.setLoop(THREE.LoopRepeat,Infinity);mixer.update(0);}
  playing=false;ui.play.textContent='Play';ui.scrub.value=0;ui.time.textContent='0.000 s';
}
async function load(){
  const token=++generation;ui.status.textContent='Loading exported GLB…';
  ui.lod.disabled=true;
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
      node.castShadow=true;node.receiveShadow=true;
      // Skinned bounds change with animation; never cull against stale bind-pose bounds.
      node.frustumCulled=false;
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
    setClip(ui.clip.value);
    ui.stats.textContent=`${Math.round(triangles).toLocaleString()} triangles\n${vertices.toLocaleString()} exported vertices\n${bones} bones · ${materials.size} material\n${clips.length} animation clips\nMaps: ${[...maps].join(', ')}\nLoaded: ${url.pathname.split('/').slice(-2).join('/')}`;
    ui.status.textContent='Export loaded · ready to inspect';
  }catch(error){ui.status.textContent=`Model load failed: ${error.message}`;console.error(error);}
  finally{ui.lod.disabled=false;}
}
ui.clip.addEventListener('change',()=>setClip(ui.clip.value));
ui.play.addEventListener('click',()=>{if(!action)return;playing=!playing;ui.play.textContent=playing?'Pause':'Play';});
ui.restart.addEventListener('click',()=>{if(action){action.reset().play();mixer.update(0);ui.scrub.value=0;}});
ui.scrub.addEventListener('input',()=>{if(!action)return;playing=false;ui.play.textContent='Play';action.time=Number(ui.scrub.value)*action.getClip().duration;mixer.update(0);});
ui.lod.addEventListener('change',load);
ui.wire.addEventListener('change',()=>model?.traverse(node=>{for(const mat of Array.isArray(node.material)?node.material:[node.material])if(mat)mat.wireframe=ui.wire.checked;}));
ui.rig.addEventListener('change',()=>{if(skeleton)skeleton.visible=ui.rig.checked;});
ui.lighting.addEventListener('change',()=>{const neutral=ui.lighting.value==='neutral';scene.background.set(neutral?'#777b7c':'#172a32');scene.fog.color.copy(scene.background);ground.material.color.set(neutral?'#777b7c':'#203941');key.color.set(neutral?0xffffff:0xffe5cc);fill.color.set(neutral?0xffffff:0xa1e0ff);scene.environmentIntensity=neutral?1:.7;key.intensity=neutral?2:3.2;});
for(const [button,position] of [[ui.front,[0,.9,3.0]],[ui.back,[0,.9,-3.0]],[ui.reset,[1.6,1.35,2.65]]])button.addEventListener('click',()=>{controls.target.set(0,.75,0);camera.position.set(...position);controls.update();});
renderer.setAnimationLoop(now=>{
  const delta=Math.min((now-last)/1000,.05);last=now;
  if(playing&&mixer)mixer.update(delta);
  if(action){ui.time.textContent=`${action.time.toFixed(3)} s`;if(playing)ui.scrub.value=action.time/action.getClip().duration;}
  controls.update();renderer.render(scene,camera);
});
load();
