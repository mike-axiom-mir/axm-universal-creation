/** Engine-neutral follower. Apply its output to the imported GLB root node.
 * Animation supplies local bob/rotor motion; this helper supplies hero following.
 * Coordinates: metres, Y up, +Z forward. It does not perform obstacle avoidance.
 */
export class CompanionFollower {
  constructor({offset=[.90,2.30,0],response=6}={}) {
    if(offset.length!==3 || !offset.every(Number.isFinite) || !Number.isFinite(response) || response<=0) throw new Error('Invalid follower settings');
    this.offset=[...offset];this.response=response;this.position=null;this.yaw=0;
  }
  reset(){this.position=null;}
  update(heroPosition,heroYaw,dt) {
    if(heroPosition.length!==3 || !heroPosition.every(Number.isFinite) || !Number.isFinite(heroYaw) || !Number.isFinite(dt) || dt<0) throw new Error('Invalid hero transform or elapsed time');
    const [x,y,z]=this.offset,c=Math.cos(heroYaw),s=Math.sin(heroYaw);
    const goal=[heroPosition[0]+c*x+s*z,heroPosition[1]+y,heroPosition[2]-s*x+c*z];
    if(this.position===null){this.position=goal;this.yaw=heroYaw;}
    else {
      const a=-Math.expm1(-this.response*dt);
      this.position=this.position.map((v,i)=>v+(goal[i]-v)*a);
      this.yaw+=Math.atan2(Math.sin(heroYaw-this.yaw),Math.cos(heroYaw-this.yaw))*a;
    }
    return {position:[...this.position],yaw:this.yaw};
  }
}
