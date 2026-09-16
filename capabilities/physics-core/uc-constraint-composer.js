'use strict';

const Core = require('./source/axm-physics-core.js');
const DistanceJoints = require('./uc-distance-joints.js');
const TranslationMounts = require('./uc-translation-mounts.js');

const VERSION = '0.1.0';
const STEP_SCHEMA = 'axm.uc-constraint-composer-step/v0.1';
const SIMULATION_SCHEMA = 'axm.uc-constraint-composer-simulation/v0.1';
const FAMILY_ORDER = Object.freeze(['translation-mounts', 'distance-joints']);
const MAX_FAMILY_PASSES = 16;

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

function normalizeConstraints(world, constraints) {
  constraints = constraints || {};
  return {
    mounts: TranslationMounts.normalizeMounts(constraints.mounts || [], world),
    distanceJoints: DistanceJoints.normalizeJoints(constraints.distanceJoints || [], world)
  };
}

function stageOptions(options, stage) {
  const post = stage === 'post';
  return {
    passes: passCount(options[post ? 'postPasses' : 'prePasses'], post ? 2 : 1),
    mounts: {
      positionIterations: iterationCount(options[post ? 'postMountPositionIterations' : 'mountPositionIterations'], post ? 2 : 4),
      velocityIterations: iterationCount(options[post ? 'postMountVelocityIterations' : 'mountVelocityIterations'], post ? 1 : 2)
    },
    distanceJoints: {
      positionIterations: iterationCount(options[post ? 'postDistancePositionIterations' : 'distancePositionIterations'], post ? 2 : 4),
      velocityIterations: iterationCount(options[post ? 'postDistanceVelocityIterations' : 'distanceVelocityIterations'], post ? 1 : 2)
    }
  };
}

function measure(world, normalized) {
  const mounts = normalized.mounts.map(mount => TranslationMounts.measureMount(world, mount));
  const distanceJoints = normalized.distanceJoints.map(joint => DistanceJoints.measureJoint(world, joint));
  return {
    mounts,
    distanceJoints,
    maxMountError: round(mounts.reduce((max, item) => Math.max(max, item.errorDistance), 0)),
    maxDistanceError: round(distanceJoints.reduce((max, item) => Math.max(max, Math.abs(item.error)), 0))
  };
}

function solveFamilies(world, normalized, stageConfig) {
  let out = clone(world);
  const passSummaries = [];

  for (let pass = 0; pass < stageConfig.passes; pass++) {
    const summary = {
      pass: pass + 1,
      familyOrder: FAMILY_ORDER.slice(),
      mountPositionReceiptCount: 0,
      mountVelocityReceiptCount: 0,
      distancePositionReceiptCount: 0,
      distanceVelocityReceiptCount: 0
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

    summary.after = measure(out, normalized);
    passSummaries.push(summary);
  }

  return { world: out, passSummaries };
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
  let normalized = { mounts: [], distanceJoints: [] };

  if (core.ok) {
    try {
      normalized = normalizeConstraints(world, constraints);
    } catch (error) {
      errors.push(error.message);
    }
  }

  const warnings = [
    'Constraint families execute in fixed deterministic order: translation mounts, then distance joints.',
    'The composer combines existing translation-only constraint families around one donor-core integration step; it does not add angular joint semantics.',
    'Conflicting constraints can retain residual error because this bounded composer does not claim a globally convergent rigid-body constraint solution.',
    'Post-core projection can move bodies after contact evidence was generated; core contacts remain explicitly tied to the pre-post-stabilization core stage.',
    'The imported donor source remains untouched.'
  ];

  if (!normalized.mounts.length && !normalized.distanceJoints.length) {
    warnings.push('No constraints were supplied; the composer would reduce to one donor-core step.');
  }

  return {
    ok: errors.length === 0,
    errors,
    mountCount: normalized.mounts.length,
    distanceJointCount: normalized.distanceJoints.length,
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
      contactEvidenceBasis: finalDiagnostics.contactEvidenceBasis
    },
    core: {
      diagnostics: clone(coreStep.diagnostics),
      events: clone(coreStep.events),
      worldBeforePostCompositeStabilization: clone(coreStep.world)
    },
    evidence: [
      normalized.mounts.length + ' translation mount(s) and ' + normalized.distanceJoints.length + ' distance joint(s) normalized once from the caller input state',
      'Constraint family order fixed as ' + FAMILY_ORDER.join(' -> '),
      preConfig.passes + ' bounded pre-core family pass(es) executed around one shared constraint state',
      'AXM Physics Core v' + Core.VERSION + ' executed exactly one collision/integration step',
      postConfig.passes + ' bounded post-core family pass(es) executed without a second integration step',
      'Final maximum mount error ' + after.maxMountError + '; final maximum distance error ' + after.maxDistanceError,
      'Final state checksum ' + Core.checksum(post.world)
    ],
    limitations: [
      'The composer currently supports only the existing translation-mount and center-to-center distance-joint families.',
      'Family order is deterministic but introduces ordering bias; conflicting constraints are bounded by pass counts rather than claimed to converge globally.',
      'No angular inertia, rotating local anchors, hinge, slider, weld, motor or gear semantics are implemented.',
      'Post-core projection can change positions after collision/contact evidence was generated; returned core events and contact geometry describe the core stage before post-composite stabilization.',
      'Connected constrained bodies can still collide unless caller collision filters suppress that pair.',
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
  normalizeConstraints,
  validate,
  step,
  simulate
};
