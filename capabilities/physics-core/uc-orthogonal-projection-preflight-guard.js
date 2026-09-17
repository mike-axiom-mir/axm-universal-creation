'use strict';

const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const BaseGuard = require('./uc-constraint-preflight-guard.js');
const OrthogonalPreflight = require('./uc-orthogonal-projection-preflight.js');

const VERSION = '0.3.0';
const STEP_SCHEMA = 'axm.uc-orthogonal-projection-preflight-guard-step/v0.3';

function clone(value) {
  if (Array.isArray(value)) return value.map(clone);
  if (value && typeof value === 'object') {
    const out = {};
    Object.keys(value).forEach(key => { out[key] = clone(value[key]); });
    return out;
  }
  return value;
}

function blockedResult(world, composerValidation, preflight, reason, evidence, limitations) {
  const checksum = Core.checksum(world);
  const blocked = {
    schema: STEP_SCHEMA,
    version: VERSION,
    ok: false,
    accepted: false,
    blocked: true,
    reason,
    world: clone(world),
    composerValidation: clone(composerValidation),
    preflight: clone(preflight),
    worldChecksumBefore: checksum,
    worldChecksumAfter: checksum,
    coreStepExecuted: false,
    composer: null,
    evidence: evidence.concat([
      'World state remained unchanged at checksum ' + checksum,
      'No donor-core step was executed.'
    ]),
    limitations
  };
  blocked.decisionChecksum = BaseGuard.decisionChecksum(blocked);
  return blocked;
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
    return blockedResult(
      world,
      composerValidation,
      preflight,
      'PROVABLE_ORTHOGONAL_LOCAL_CONFLICT',
      [
        preflight.counts.orthogonalProjectionRadialConflicts + ' bounded same-pair orthogonal projection/radial conflict(s) blocked before donor integration.',
        'Radial-maximum conflicts use orthogonal projection lower bounds; radial-minimum conflicts require finite upper bounds on both orthogonal projections.'
      ],
      [
        'This is an opt-in stronger guard layered in front of the existing fail-closed preflight guard; the existing guard and composer are unchanged.',
        'Only two same-body-pair unit projection groups that are mutually orthogonal within a strict tolerance are combined at once.',
        'The proof uses the 2D orthonormal identity distance^2 = projectionA^2 + projectionB^2.',
        'Radial minima are considered only when both orthogonal projection intervals have finite maximum magnitudes; unbounded intervals are not guessed closed.',
        'Oblique directions, multi-pair geometry, loops and global satisfiability remain outside this guard.',
        'A blocked result is local contradiction evidence, not a claim of general physical correctness or scientific validation.'
      ]
    );
  }

  if (!preflight.strongerProofComplete && preflight.proofBudget && preflight.proofBudget.exhausted) {
    const budget = preflight.proofBudget.maxProjectionPairCandidates;
    return blockedResult(
      world,
      composerValidation,
      preflight,
      'ORTHOGONAL_PROOF_BUDGET_EXHAUSTED',
      [
        'The configured stronger-proof candidate budget was exhausted before every same-pair projection candidate could be evaluated.',
        preflight.counts.projectionPairCandidates + ' of ' + preflight.counts.projectionPairCandidatesAvailable + ' candidate pair(s) were evaluated.',
        'The explicit candidate budget was ' + budget + '; incomplete stronger-proof coverage is blocked rather than silently delegated.'
      ],
      [
        'Budget exhaustion is not evidence that the constraints are contradictory; it is a fail-closed execution decision for incomplete optional stronger-proof coverage.',
        'Default behavior remains unbounded and therefore unchanged unless maxProjectionPairCandidates is explicitly supplied.',
        'The budget changes proof work only; it does not alter the base conservative preflight, composer, donor core or solver semantics.',
        'Only two same-body-pair unit projection groups that are mutually orthogonal within a strict tolerance are eligible for stronger proof.',
        'Oblique directions, multi-pair geometry, loops and global satisfiability remain outside this guard.',
        'A blocked result is bounded execution evidence, not a claim of physical correctness or scientific validation.'
      ]
    );
  }

  // Conflict-free complete extended evidence does not create another solver path.
  // Delegate exactly once to the already-established guard/composer chain.
  return BaseGuard.step(world, constraints, dt, options.baseGuard || options);
}

module.exports = {
  VERSION,
  STEP_SCHEMA,
  step
};
