'use strict';

const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const BaseGuard = require('./uc-constraint-preflight-guard.js');
const OrthogonalPreflight = require('./uc-orthogonal-projection-preflight.js');

const VERSION = '0.2.0';
const STEP_SCHEMA = 'axm.uc-orthogonal-projection-preflight-guard-step/v0.2';

function clone(value) {
  if (Array.isArray(value)) return value.map(clone);
  if (value && typeof value === 'object') {
    const out = {};
    Object.keys(value).forEach(key => { out[key] = clone(value[key]); });
    return out;
  }
  return value;
}

function step(world, constraints, dt, options) {
  options = options || {};
  const composerValidation = Composer.validate(world, constraints);
  const preflight = OrthogonalPreflight.analyze(world, constraints, options.preflight || {});

  // Preserve the existing guard's reason ordering and accepted path for all
  // cases already covered by the established preflight.
  if (!composerValidation.ok || !preflight.base.valid || preflight.counts.baseConflicts > 0) {
    return BaseGuard.step(world, constraints, dt, options.baseGuard || options);
  }

  if (preflight.counts.orthogonalProjectionRadialConflicts > 0) {
    const checksum = Core.checksum(world);
    const blocked = {
      schema: STEP_SCHEMA,
      version: VERSION,
      ok: false,
      accepted: false,
      blocked: true,
      reason: 'PROVABLE_ORTHOGONAL_LOCAL_CONFLICT',
      world: clone(world),
      composerValidation: clone(composerValidation),
      preflight: clone(preflight),
      worldChecksumBefore: checksum,
      worldChecksumAfter: checksum,
      coreStepExecuted: false,
      composer: null,
      evidence: [
        preflight.counts.orthogonalProjectionRadialConflicts + ' bounded same-pair orthogonal projection/radial conflict(s) blocked before donor integration.',
        'Radial-maximum conflicts use orthogonal projection lower bounds; radial-minimum conflicts require finite upper bounds on both orthogonal projections.',
        'World state remained unchanged at checksum ' + checksum,
        'No donor-core step was executed.'
      ],
      limitations: [
        'This is an opt-in stronger guard layered in front of the existing fail-closed preflight guard; the existing guard and composer are unchanged.',
        'Only two same-body-pair unit projection groups that are mutually orthogonal within a strict tolerance are combined at once.',
        'The proof uses the 2D orthonormal identity distance^2 = projectionA^2 + projectionB^2.',
        'Radial minima are considered only when both orthogonal projection intervals have finite maximum magnitudes; unbounded intervals are not guessed closed.',
        'Oblique directions, multi-pair geometry, loops and global satisfiability remain outside this guard.',
        'A blocked result is local contradiction evidence, not a claim of general physical correctness or scientific validation.'
      ]
    };
    blocked.decisionChecksum = BaseGuard.decisionChecksum(blocked);
    return blocked;
  }

  // Conflict-free extended evidence does not create another solver path.
  // Delegate exactly once to the already-established guard/composer chain.
  return BaseGuard.step(world, constraints, dt, options.baseGuard || options);
}

module.exports = {
  VERSION,
  STEP_SCHEMA,
  step
};
