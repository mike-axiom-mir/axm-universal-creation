/** Engine-neutral, flat-ground kinematic vehicle. Metres, Y-up, +Z forward.
 * A game applies position/yaw to the vehicle root and the returned angles to
 * each named bone's local Y rotation relative to its bind pose.
 * Do not simultaneously play Drive_Cycle over the controlled wheel bones.
 * This is a driving starter, not a physics/contact solver.
 */
export class TrikeDrive {
  constructor({position=[0,0,0],yaw=0,maxForward=14,maxReverse=4}={}) {
    if(!Array.isArray(position)||position.length!==3||!position.every(Number.isFinite)||!Number.isFinite(yaw)||![maxForward,maxReverse].every(x=>Number.isFinite(x)&&x>0))throw new TypeError('Invalid vehicle configuration');
    this.position=[...position];this.yaw=yaw;this.speed=0;this.steer=0;this.distance=0;
    this.maxForward=maxForward;this.maxReverse=maxReverse;
  }
  update({throttle=0,steer=0,brake=0}={},dt=0) {
    if(![throttle,steer,brake,dt].every(Number.isFinite)||dt<0||dt>1)throw new RangeError('Finite inputs and dt between 0 and 1 second required');
    throttle=Math.max(-1,Math.min(1,throttle));steer=Math.max(-1,Math.min(1,steer));brake=Math.max(0,Math.min(1,brake));
    const count=Math.max(1,Math.ceil(dt*120)),h=dt/count;
    for(let i=0;i<count;i++){
      this.steer+=(steer*.48-this.steer)*(-Math.expm1(-8*h));
      const acceleration=throttle*5;
      let speed=this.speed+acceleration*h;
      const deceleration=(.6+Math.abs(speed)*.10+brake*12)*h;
      speed=Math.sign(speed)*Math.max(0,Math.abs(speed)-deceleration);
      speed=Math.max(-this.maxReverse,Math.min(this.maxForward,speed));
      const ds=(this.speed+speed)*.5*h;
      const turn=ds*Math.tan(this.steer)/1.93;
      this.position[0]+=Math.sin(this.yaw+turn*.5)*ds;
      this.position[2]+=Math.cos(this.yaw+turn*.5)*ds;
      this.yaw+=turn;this.distance+=ds;this.speed=speed;
    }
    return this.snapshot();
  }
  snapshot(){
    return {position:[...this.position],yaw:this.yaw,speed:this.speed,
      boneLocalY:{'Steering':this.steer,'SteeringWheel':this.steer*1.5,
      'Wheel.Front':this.distance/.64,'Wheel.Rear.L':this.distance/.49,'Wheel.Rear.R':this.distance/.49}};
  }
}
