import fs from 'node:fs';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';import path from 'node:path';
const [game,defender,launcher,out]=process.argv.slice(2);
const base=pathToFileURL(path.resolve(game)+path.sep);
const {GLTFLoader}=await import(new URL('vendor/GLTFLoader.js',base));
const {DefenderVisual}=await import(new URL('defender-animation.mjs',base));
const {createMotor}=await import(new URL('motor.mjs',base));
const parse=async p=>{const b=fs.readFileSync(p);return(await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'')).scene;};
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const suit=await parse(defender),weapon=await parse(launcher),cases=[];
const names=['Pelvis','Torso','Head',...['Left','Right'].flatMap(s=>['Shoulder','Elbow','Wrist','Hip','Knee','Ankle'].map(n=>n+s))];
for(const height of [1.8,1.05])for(const pitch of [-1.25,-1,-.5,0,.5,1,1.25])for(const recoil of pitch===0?[0,1]:[0]){
 const rig=new DefenderVisual(suit,'#77dcff'),p={x:0,z:0,yaw:Math.PI,pitch,recoil,hp:100,motor:createMotor()};p.motor.height=height;
 rig.equip(weapon,'Tourist');for(let i=0;i<120;i++)rig.update(p,1/60,()=>0);
 const trs=o=>({position:o.position.toArray(),quaternion_xyzw:o.quaternion.toArray(),scale:o.scale.toArray()});
 cases.push({name:`${height===1.8?'standing':'crouch'}-pitch${pitch}-recoil${recoil}`,joint_transforms:Object.fromEntries(names.map(n=>[n,trs(rig.nodes[n])])),weapon:trs(rig.weapon),hand_errors:rig.aimErrors});rig.dispose();
}
const report={defender_sha256:sha(defender),launcher_sha256:sha(launcher),animation_sha256:sha(new URL('defender-animation.mjs',base)),motor_sha256:sha(new URL('motor.mjs',base)),cases};
fs.writeFileSync(out,JSON.stringify(report,null,2));console.log(JSON.stringify({cases:cases.length,max_hand_error_m:Math.max(...cases.flatMap(c=>Object.values(c.hand_errors)))}));
