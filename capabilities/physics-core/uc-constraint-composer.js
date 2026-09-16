'use strict';

const Core = require('./source/axm-physics-core.js');
const DistanceJoints = require('./uc-distance-joints.js');
const DistanceLimits = require('./uc-distance-limits.js');
const TranslationMounts = require('./uc-translation-mounts.js');

const VERSION = '0.3.0';
const STEP_SCHEMA = 'axm.uc-constraint-composer-step/v0.1';
const SIMULATION_SCHEMA = 'axm.uc-constraint-composer-simulation/v0.1';
const FAMILY_ORDER = Object.freeze(['translation-mounts', 'distance-joints', 'distance-limits']);
const MAX_FAMILY_PASSES = 16;
const DEFAULT_POSITION_TOLERANCE = 1e-8;
const DEFAULT_VELOCITY_TOLERANCE = 1e-8;
const MAX_CONVERGENCE_TOLERANCE = 1e6;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function finite(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function bounded(value, min, max, fallback) {
  return Math.max(min, Math.min(max, finite(value, fallback)));
}

function iterationCount(value, fallback) {
  return Math.round(bounded(value, 0, 32, fallback));
}

function passCount(value, fallback) {
  return Math.round(bounded(value, 1, MAX_FAMILY_PASSES, fallback));
}

function round(value) {
  return Math.round(value * 1e9) / 1e9;
}

function body(world, id) {
  return (world.bodies || []).find(item => item.id === id) || null;
}

function velocity(item) {
  const v = item && item.velocity ? item.velocity : {};
  return { x: finite(v.x, 0), y: finite(v.y, 0) };
}

function normalizeConstraints(world, constraints) {
  constraints = constraints || {};
  return {
    mounts: TranslationMounts.normalizeMounts(constraints.mounts || [], world),
    distanceJoints: DistanceJoints.normalizeJoints(constraints.distanceJoints || [], world),
    distanceLimits: DistanceLimits.normalizeLimits(constraints.distanceLimits || [], world)
  };
}

function optionEnabled(options, key, fallback) {
  if (!Object.prototype.hasOwnProperty.call(options, key)) return fallback;
  return options[key] !== false;
}

function stageOptions(options, stage) {
  const post = stage === 'post';
  const prefix = post ? 'post' : 'pre';
  const globalEarlyExit = optionEnabled(options, 'earlyExit', true);
  const globalPositionTolerance = bounded(options.positionTolerance, 0, MAX_CONVERGENCE_TOLERANCE, DEFAULT_POSITION_TOLERANCE);
  const globalVelocityTolerance = bounded(options.velocityTolerance, 0, MAX_CONVERGENCE_TOLERANCE, DEFAULT_VELOCITY_TOLERANCE);
  return {
    passes: passCount(options[post ? 'postPasses' : 'prePasses'], post ? 2 : 1),
    earlyExit: optionEnabled(options, prefix + 'EarlyExit', globalEarlyExit),
    positionTolerance: bounded(options[prefix + 'PositionTolerance'], 0, MAX_CONVERGENCE_TOLERANCE, globalPositionTolerance),
    velocityTolerance: bounded(options[prefix + 'VelocityTolerance'], 0, MAX_CONVERGENCE_TOLERANCE, globalVelocityTolerance),
    mounts: {
      positionIterations: iterationCount(options[post ? 'postMountPositionIterations' : 'mountPositionIterations'], post ? 2 : 4),
      velocityIterations: iterationCount(options[post ? 'postMountVelocityIterations' : 'mountVelocityIterations'], post ? 1 : 2)
    },
    distanceJoints: {
      positionIterations: iterationCount(options[post ? 'postDistancePositionIterations' : 'distancePositionIterations'], post ? 2 : 4),
      velocityIterations: iterationCount(options[post ? 'postDistanceVelocityIterations' : 'distanceVelocityIterations'], post ? 1 : 2)
    },
    distanceLimits: {
      positionIterations: iterationCount(options[post ? 'postLimitPositionIterations' : 'limitPositionIterations'], post ? 2 : 4),
      velocityIterations: iterationCount(options[post ? 'postLimitVelocityIterations' : 'limitVelocityIterations'], post ? 1 : 2)
    }
  };
}

function mountRelativeSpeed(world, mount) {
  const a = body(world, mount.a);
  const b = body(world, mount.b);
  if (!a || !b) return 0;
  const av = velocity(a);
  const bv = velocity(b);
  return Math.hypot(bv.x - av.x, bv.y - av.y);
}

function distanceRelativeSpeed(world, joint) {
  const a = body(world, joint.a);
  const b = body(world, joint.b);
  if (!a || !b) return 0;
  const dx = b.position.x - a.position.x;
  const dy = b.position.y - a.position.y;
  const distance = Math.hypot(dx, dy);
  const axisX = distance > 1e-12 ? dx / distance : 1;
  const axisY = distance > 1e-12 ? dy / distance : 0;
  const av = velocity(a);
  const bv = velocity(b);
  return Math.abs((bv.x - av.x) * axisX + (bv.y - av.y) * axisY);
}

function distanceLimitRelativeSpeed(world, limit) {
  if (!limit.enabled) return 0;
  const violation = DistanceLimits.velocityViolation(world, limit);
  return violation.active ? Math.abs(violation.relativeSpeed) : 0;
}

function measure(world, normalized) {
  const mounts = normalized.mounts.map(mount => TranslationMounts.measureMount(world, mount));
  const distanceJoints = normalized.distanceJoints.map(joint => DistanceJoints.measureJoint(world, joint));
  const distanceLimits = normalized.distanceLimits.map(limit => DistanceLimits.measureLimit(world, limit));
  return {
    mounts,
    distanceJoints,
    distanceLimits,
    maxMountError: round(mounts.reduce((max, item) => Math.max(max, item.errorDistance), 0)),
    maxDistanceError: round(distanceJoints.reduce((max, item) => Math.max(max, Math.abs(item.error)), 0)),
    maxDistanceLimitError: round(distanceLimits.reduce((max, item) => item.enabled ? Math.max(max, Math.abs(item.error)) : max, 0)),
    maxMountRelativeSpeed: round(normalized.mounts.reduce((max, mount) => Math.max(max, mountRelativeSpeed(world, mount)), 0)),
    maxDistanceRelativeSpeed: round(normalized.distanceJoints.reduce((max, joint) => Math.max(max, distanceRelativeSpeed(world, joint)), 0)),
    maxDistanceLimitRelativeSpeed: round(normalized.distanceLimits.reduce((max, limit) => Math.max(max, distanceLimitRelativeSpeed(world, limit)), 0))
  };
}

function convergence(measurement, stageConfig) {
  const maxPositionError = round(Math.max(measurement.maxMountError, measurement.maxDistanceError, measurement.maxDistanceLimitError));
  const maxVelocityError = round(Math.max(measurement.maxMountRelativeSpeed, measurement.maxDistanceRelativeSpeed, measurement.maxDistanceLimitRelativeSpeed));
  return {
    converged: maxPositionError <= stageConfig.positionTolerance && maxVelocityError <= stageConfig.velocityTolerance,
    maxPositionError,
    maxVelocityError,
    positionTolerance: stageConfig.positionTolerance,
    velocityTolerance: stageConfig.velocityTolerance
  };
}

function solveFamilies(world, normalized, stageConfig) {
  let out = clone(world);
  const passSummaries = [];
  let earlyExitTriggered = false;

  for (let pass = 0; pass < stageConfig.passes; pass++) {
    const summary = {
      pass: pass + 1,
      familyOrder: FAMILY_ORDER.slice(),
      mountPositionReceiptCount: 0,
      mountVelocityReceiptCount: 0,
      distancePositionReceiptCount: 0,
      distanceVelocityReceiptCount: 0,
      distanceLimitPositionReceiptCount: 0,
      distanceLimitVelocityReceiptCount: 0
    };

    if (normalized.mounts.length) {
      const preparedMounts = TranslationMounts.prepareWorld(out, normalized.mounts, stageConfig.mounts);
      out = preparedMounts.world;
      summary.mountPositionReceiptCount = preparedMounts.positionReceipts.length;
      summary.mountVelocityReceiptCount = preparedMounts.velocityReceipts.length;
    }

    if (normalized.distanceJoints.length) {
      const preparedJoints = DistanceJoints.prepareWorld(out, normalized.distanceJoints, stageConfig.distanceJoints);
      out = preparedJoints.world;
      summary.distancePositionReceiptCount = preparedJoints.positionReceipts.length;
      summary.distanceVelocityReceiptCount = preparedJoints.velocityReceipts.length;
    }

    if (normalized.distanceLimits.length) {
      const preparedLimits = DistanceLimits.prepareWorld(out, normalized.distanceLimits, stageConfig.distanceLimits);
      out = preparedLimits.world;
      summary.distanceLimitPositionReceiptCount = preparedLimits.positionReceipts.length;
      summary.distanceLimitVelocityReceiptCount = preparedLimits.velocityReceipts.length;
    }

    summary.after = measure(out, normalized);
    summary.convergence = convergence(summary.after, stageConfig);
    passSummaries.push(summary);

    if (stageConfig.earlyExit && summary.convergence.converged && pass + 1 < stageConfig.passes) {
      earlyExitTriggered = true;
      summary.stoppedEarly = true;
      break;
    }
  }

  return {
    world: out,
    passSummaries,
    passesExecuted: passSummaries.length,
    passesAvoided: Math.max(0, stageConfig.passes - passSummaries.length),
    earlyExitTriggered
  };
}

function refreshDiagnostics(world, coreDiagnostics, beforeCoreDiagnostics) {
  const refreshed = Core.measure(
    world,
    coreDiagnostics.substeps,
    coreDiagnostics.maxPenetration,
    coreDiagnostics.broadphasePairs,
    {
      overflowBodies: coreDiagnostics.broadphaseOverflowBodies,
      cellEntries: coreDiagnostics.broadphaseCellEntries,
      occupiedCells: coreDiagnostics.broadphaseOccupiedCells,
      warmStartedContacts: coreDiagnostics.warmStartedContacts,
      warmStartAppliedImpulse: coreDiagnostics.warmStartAppliedImpulse,
      warmStartCorrectionImpulse: coreDiagnostics.warmStartCorrectionImpulse,
      detectedUniqueContacts: coreDiagnostics.detectedUniqueContacts
    }
  );
  refreshed.energyDelta = round(refreshed.totalEnergy - beforeCoreDiagnostics.totalEnergy);
  refreshed.constraintComposerPostStabilized = true;
  refreshed.contactEvidenceBasis = 'CORE_STAGE_BEFORE_POST_COMPOSITE_STABILIZATION';
  world.diagnostics = refreshed;
  return refreshed;
}

function validate(world, constraints) {
  const core = Core.validate(world);
  const errors = (core.errors || []).slice();
  let normalized = { mounts: [], distanceJoints: [], distanceLimits: [] };

  if (core.ok) {
    try {
      normalized = normalizeConstraints(world, constraints);
    } catch (error) {
      errors.push(error.message);
    }
  }

  const warnings = [
    'Constraint families execute in fixed deterministic order: translation mounts, then distance joints, then distance limits.',
    'Distance-limit range interiors remain slack; only violated position bounds or outward-moving active boundaries contribute residuals and correction.',
    'The composer combines existing translation-only constraint families around one donor-core integration step; it does not add angular joint semantics.',
    'Convergence-aware early exit is tolerance-based and requires both position and constrained relative-velocity residuals to satisfy caller-visible thresholds; it is not proof of global convergence.',
    'Conflicting constraints can retain residual error because this bounded composer does not claim a globally convergent rigid-body constraint solution.',
    'Post-core projection can move bodies after contact evidence was generated; core contacts remain explicitly tied to the pre-post-stabilization core stage.',
    'The imported donor source remains untouched.'
  ];

  if (!normalized.mounts.length && !normalized.distanceJoints.length && !normalized.distanceLimits.length) {
    warnings.push('No constraints were supplied; the composer would reduce to one donor-core step.');
  }

  return {
    ok: errors.length === 0,
    errors,
    mountCount: normalized.mounts.length,
    distanceJointCount: normalized.distanceJoints.length,
    distanceLimitCount: normalized.distanceLimits.length,
    warnings
  };
}

function step(world, constraints, dt, options) {
  const validation = validate(world, constraints);
  if (!validation.ok) throw new Error(validation.errors.join('; '));

  options = options || {};
  const normalized = normalizeConstraints(world, constraints);
  const preConfig = stageOptions(options, 'pre');
  const postConfig = stageOptions(options, 'post');
  const initial = measure(world, normalized);

  const pre = solveFamilies(world, normalized, preConfig);
  const afterPreSolve = measure(pre.world, normalized);
  const beforeCoreDiagnostics = Core.measure(pre.world, 0, 0);
  const coreStep = Core.step(pre.world, dt);
  const afterCore = measure(coreStep.world, normalized);

  const post = solveFamilies(coreStep.world, normalized, postConfig);
  const after = measure(post.world, normalized);
  const finalDiagnostics = refreshDiagnostics(post.world, coreStep.diagnostics, beforeCoreDiagnostics);
  const totalPassBudget = preConfig.passes + postConfig.passes;
  const totalPassesExecuted = pre.passesExecuted + post.passesExecuted;
  const totalPassesAvoided = pre.passesAvoided + post.passesAvoided;

  return {
    schema: STEP_SCHEMA,
    ok: true,
    world: post.world,
    constraints: clone(normalized),
    composerDiagnostics: {
      familyOrder: FAMILY_ORDER.slice(),
      preConfig: clone(preConfig),
      postConfig: clone(postConfig),
      initial,
      afterPreSolve,
      afterCore,
      after,
      prePassSummaries: pre.passSummaries,
      postPassSummaries: post.passSummaries,
      prePassesExecuted: pre.passesExecuted,
      postPassesExecuted: post.passesExecuted,
      prePassesAvoided: pre.passesAvoided,
      postPassesAvoided: post.passesAvoided,
      totalPassBudget,
      totalPassesExecuted,
      totalPassesAvoided,
      earlyExitTriggered: pre.earlyExitTriggered || post.earlyExitTriggered,
      contactEvidenceBasis: finalDiagnostics.contactEvidenceBasis
    },
    core: {
      diagnostics: clone(coreStep.diagnostics),
      events: clone(coreStep.events),
      worldBeforePostCompositeStabilization: clone(coreStep.world)
    },
    evidence: [
      normalized.mounts.length + ' translation mount(s), ' + normalized.distanceJoints.length + ' distance joint(s), and ' + normalized.distanceLimits.length + ' distance limit(s) normalized once from the caller input state',
      'Constraint family order fixed as ' + FAMILY_ORDER.join(' -> '),
      pre.passesExecuted + ' of ' + preConfig.passes + ' bounded pre-core family pass(es) executed',
      'AXM Physics Core v' + Core.VERSION + ' executed exactly one collision/integration step',
      post.passesExecuted + ' of ' + postConfig.passes + ' bounded post-core family pass(es) executed without a second integration step',
      'Convergence-aware early exit avoided ' + totalPassesAvoided + ' of ' + totalPassBudget + ' configured family pass(es)',
      'Final maximum mount error ' + after.maxMountError + '; final maximum distance-joint error ' + after.maxDistanceError + '; final maximum distance-limit violation ' + after.maxDistanceLimitError,
      'Final constrained relative-speed maxima: mounts ' + after.maxMountRelativeSpeed + '; distance joints ' + after.maxDistanceRelativeSpeed + '; active distance limits ' + after.maxDistanceLimitRelativeSpeed,
      'Final state checksum ' + Core.checksum(post.world)
    ],
    limitations: [
      'The composer currently supports only the existing translation-mount, center-to-center distance-joint, and center-distance-limit families.',
      'Distance-limit range interiors are intentionally slack and are not treated as zero-error exact joints.',
      'Family order is deterministic but introduces ordering bias; conflicting constraints are bounded by pass counts rather than claimed to converge globally.',
      'Early exit only means configured position and constrained relative-velocity tolerances were satisfied at a pass boundary; it is not a proof of physical equilibrium or global convergence.',
      'No angular inertia, rotating local anchors, hinge, slider, weld, motor or gear semantics are implemented.',
      'Post-core projection can change positions after collision/contact evidence was generated; returned core events and contact geometry describe the core stage before post-composite stabilization.',
      'Connected constrained bodies can still collide unless caller collision filters or the separate component-isolation wrapper suppress that component.',
      'This is game/prototype physics evidence, not scientific validation.'
    ]
  };
}

function simulate(world, constraints, steps, dt, options) {
  let out = clone(world);
  const count = Math.max(1, Math.min(100000, Math.round(finite(steps, 1))));
  let last = null;

  for (let index = 0; index < count; index++) {
    last = step(out, constraints, dt, options);
    out = last.world;
  }

  return {
    schema: SIMULATION_SCHEMA,
    ok: true,
    steps: count,
    world: out,
    constraints: last ? last.constraints : normalizeConstraints(out, constraints),
    composerDiagnostics: last ? last.composerDiagnostics : null,
    checksum: Core.checksum(out),
    evidence: (last ? last.evidence : []).concat([count + ' composed-constraint step(s) completed'])
  };
}

module.exports = {
  VERSION,
  STEP_SCHEMA,
  SIMULATION_SCHEMA,
  FAMILY_ORDER,
  MAX_FAMILY_PASSES,
  DEFAULT_POSITION_TOLERANCE,
  DEFAULT_VELOCITY_TOLERANCE,
  MAX_CONVERGENCE_TOLERANCE,
  normalizeConstraints,
  validate,
  step,
  simulate
};
