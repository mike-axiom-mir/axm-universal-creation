'use strict';

module.exports = {
  core: require('./source/axm-physics-core.js'),
  sourceAdapter: require('./source/axm-physics-adapter.js'),
  fabric: require('./uc-physics-fabric.js'),
  distanceJoints: require('./uc-distance-joints.js'),
  distanceLimits: require('./uc-distance-limits.js'),
  translationMounts: require('./uc-translation-mounts.js'),
  axisLocks: require('./uc-axis-locks.js'),
  axisLimits: require('./uc-axis-limits.js'),
  constraintComposer: require('./uc-constraint-composer.js'),
  constraintCollisionIsolation: require('./uc-constraint-collision-isolation.js'),
  constraintActivityGate: require('./uc-constraint-activity-gate.js')
};
