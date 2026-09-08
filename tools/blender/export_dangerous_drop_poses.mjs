/** Sample the current game solvers with the agreed authored-sight mount. No game writes. */
import fs from 'node:fs';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';import path from 'node:path';
const [game,defender,launcher,out,weaponName]=process.argv.slice(2),base=pathToFileURL(path.resolve(game)+path.sep);
const T=await import(new URL('vendor/three.module.js',base));
const {GLTFLoader}=await import(new URL('vendor/GLTFLoader.js',base));
const {DefenderVisual}=await import(new URL('defender-animation.mjs',base));
const {FirstPersonArms}=await import(new URL('first-person-arms.mjs',base));
const {createMotor}=await import(new URL('motor.mjs',base));
const parse=async p=>{const b=fs.readFileSync(p);return(await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'')).scene;};
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const suit=await parse(defender),weapon=await parse(launcher),cases=[];
const trs=o=>({position:o.position.toArray(),quaternion_xyzw:o.quaternion.toArray(),scale:o.scale.toArray()});
const names=['Pelvis','Torso','Head',...['Left','Right'].flatMap(s=>['Shoulder','Elbow','Wrist','Hip','Knee','Ankle'].map(n=>n+s))];
for(const height of [1.8,1.05])for(const pitch of [-1.25,-1,-.5,0,.5,1,1.25])for(const recoil of pitch===0?[0,1]:[0]){
 const rig=new DefenderVisual(suit,'#77dcff'),p={x:0,z:0,yaw:Math.PI,pitch,recoil,hp:100,motor:createMotor()};p.motor.height=height;
 rig.equip(weapon,weaponName);for(let i=0;i<120;i++)rig.update(p,1/60,()=>0);
 cases.push({context:'world',name:`${height===1.8?'standing':'crouch'}-pitch${pitch}-recoil${recoil}`,joint_transforms:Object.fromEntries(names.map(n=>[n,trs(rig.nodes[n])])),weapon:trs(rig.weapon),hand_errors:rig.aimErrors});rig.dispose();
}
// These are exact current game.mjs placement formulas, with the new asset registered
// to the authored Sight path. Owner has not integrated these names at export time.
for(const aim of [0,.5,1])for(const reloadFraction of [0,.25,.5,.75])for(const recoil of [0,1]){
 const scene=new T.Scene(),arms=new FirstPersonArms(suit,'#77dcff'),gun=new T.Group(),model=weapon.clone(true);scene.add(arms.root,gun);gun.add(model);model.rotation.y=Math.PI;model.position.set(0,-.11,-.04);scene.updateMatrixWorld(true);
 const sight=gun.worldToLocal(model.getObjectByName('Sight').getWorldPosition(new T.Vector3()));
 const phase=reloadFraction?Math.sin((1-reloadFraction)*Math.PI):0,hipY=-Math.max(.34,sight.y+.06),aimY=-sight.y,aimX=-sight.x;
 gun.position.set(T.MathUtils.lerp(.23,aimX,aim),T.MathUtils.lerp(hipY,aimY,aim)-phase*.18,-.90+recoil*.06+aim*.25);
 const sidearmPose=1-aim;gun.rotation.set(recoil*.08+phase*.8-sidearmPose*.04,-sidearmPose*.12,phase*-.3);scene.updateMatrixWorld(true);
 const p={hp:100,weapon:weaponName,equippedModel:model,reload:reloadFraction,reloadMax:1};arms.update(p);scene.updateMatrixWorld(true);
 const position=new T.Vector3(),rotation=new T.Quaternion(),scale=new T.Vector3();model.matrixWorld.decompose(position,rotation,scale);
 cases.push({context:'first-person',name:`view-aim${aim}-reload${reloadFraction}-recoil${recoil}`,joint_transforms:Object.fromEntries(['Left','Right'].flatMap(side=>['shoulder','elbow','wrist'].map(key=>{const o=arms.arms[side][key];return [o.name,trs(o)];}))),weapon:{position:position.toArray(),quaternion_xyzw:rotation.toArray(),scale:scale.toArray()},hand_errors:{...arms.errors}});arms.dispose();
}
const report={weapon_name:weaponName,root_name:weapon.children[0]?.name||weapon.name,defender_sha256:sha(defender),launcher_sha256:sha(launcher),animation_sha256:sha(new URL('defender-animation.mjs',base)),first_person_arms_sha256:sha(new URL('first-person-arms.mjs',base)),motor_sha256:sha(new URL('motor.mjs',base)),observed_game_sha256:sha(new URL('game.mjs',base)),placement_reference_commit:'c218e5d',first_person_assumption:'Authored Sight placement formulas preserved in Build10 c218e5d, model rotation Y=pi and position (0,-.11,-.04), motion sway=0 and assist=0. 70 degree perspective intended. The game file fingerprint is observational; game.mjs is not executed by this sampler. Actual solver modules are imported and hashed above.',cases};
fs.writeFileSync(out,JSON.stringify(report,null,2));console.log(JSON.stringify({cases:cases.length,max_hand_error_m:Math.max(...cases.flatMap(c=>Object.values(c.hand_errors)))}));
