'use strict';

const crypto = require('crypto');
const BasePreflight = require('./uc-constraint-preflight.js');
const ExactGeometry = require('./uc-exact-projection-geometry.js');

const VERSION = '0.8.0';
const REPORT_SCHEMA = 'axm.uc-orthogonal-projection-preflight/v0.8';
const DEFAULT_ORTHOGONALITY_TOLERANCE = 1e-9;
const MAX_ORTHOGONALITY_TOLERANCE = 1e-6;
const MAX_PROJECTION_PAIR_CANDIDATE_BUDGET = 100000;

function clone(value) {
  if (Array.isArray(value)) return value.map(clone);
  if (value && typeof value === 'object') {
    const out = {};
    Object.keys(value).forEach(key => { out[key] = clone(value[key]); });
    return out;
  }
  return value;
}

function finite(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function bounded(value, min, max, fallback) {
  return Math.max(min, Math.min(max, finite(value, fallback)));
}

function projectionPairCandidateBudget(value) {
  if (value === undefined || value === null || value === Infinity) return Infinity;
  const number = Number(value);
  if (!Number.isFinite(number)) return Infinity;
  return Math.floor(Math.max(0, Math.min(MAX_PROJECTION_PAIR_CANDIDATE_BUDGET, number)));
}

function round(value) {
  return Math.round(value * 1e9) / 1e9;
}

function roundedDirection(direction) {
  return { x: round(direction.x), y: round(direction.y) };
}

function roundedInterval(interval) {
  return {
    min: Number.isFinite(interval.min) ? round(interval.min) : interval.min,
    max: Number.isFinite(interval.max) ? round(interval.max) : interval.max
  };
}

function minimumAbsoluteInterval(interval) {
  if (interval.min <= 0 && interval.max >= 0) return 0;
  return Math.min(Math.abs(interval.min), Math.abs(interval.max));
}

function maximumAbsoluteInterval(interval) {
  if (!Number.isFinite(interval.min) || !Number.isFinite(interval.max)) return Infinity;
  return Math.max(Math.abs(interval.min), Math.abs(interval.max));
}

function directionNormSquared(direction) {
  return direction.x * direction.x + direction.y * direction.y;
}

function dot(left, right) {
  return left.x * right.x + left.y * right.y;
}

function singularValueBounds(firstDirection, secondDirection) {
  const firstNormSquared = directionNormSquared(firstDirection);
  const secondNormSquared = directionNormSquared(secondDirection);
  const cross = dot(firstDirection, secondDirection);
  const trace = firstNormSquared + secondNormSquared;
  const discriminant = Math.sqrt(Math.max(
    0,
    (firstNormSquared - secondNormSquared) * (firstNormSquared - secondNormSquared) +
      4 * cross * cross
  ));
  const maximumEigenvalue = Math.max(0, (trace + discriminant) / 2);
  const minimumEigenvalue = Math.max(0, (trace - discriminant) / 2);
  return {
    min: Math.sqrt(minimumEigenvalue),
    max: Math.sqrt(maximumEigenvalue)
  };
}

function projectionMetric(group) {
  return {
    group,
    unitError: Math.abs(directionNormSquared(group.direction) - 1),
    minimumMagnitude: minimumAbsoluteInterval(group.intersection),
    maximumMagnitude: maximumAbsoluteInterval(group.intersection)
  };
}

function indexProjectionMetricsByPair(projections) {
  const indexed = new Map();
  projections.forEach(group => {
    const metric = projectionMetric(group);
    if (!indexed.has(group.pairKey)) indexed.set(group.pairKey, []);
    indexed.get(group.pairKey).push(metric);
  });
  return indexed;
}

function candidatePairCount(metrics) {
  return metrics.length < 2 ? 0 : (metrics.length * (metrics.length - 1)) / 2;
}

function constraintIds(groups) {
  return Array.from(new Set(groups.flatMap(group => (group.constraints || []).map(item => item.id)))).sort();
}

function families(groups) {
  return Array.from(new Set(groups.flatMap(group => (group.constraints || []).map(item => item.family)))).sort();
}

function radialMaximumWitness(projectionMagnitudeLowerBound, basisSingularValues, minimumRequiredDistance, maximumAllowedDistance, tolerance) {
  return {
    projectionMagnitudeLowerBound,
    basisSingularValues: clone(basisSingularValues),
    minimumRequiredDistance,
    maximumAllowedDistance,
    proofMargin: minimumRequiredDistance - maximumAllowedDistance,
    tolerance
  };
}

function radialMinimumWitness(minimumAllowedDistance, projectionMagnitudeUpperBound, basisSingularValues, maximumPossibleDistance, tolerance) {
  return {
    minimumAllowedDistance,
    projectionMagnitudeUpperBound,
    basisSingularValues: clone(basisSingularValues),
    maximumPossibleDistance,
    proofMargin: minimumAllowedDistance - maximumPossibleDistance,
    tolerance
  };
}

function reportChecksum(report) {
  const basis = {
    schema: report.schema,
    version: report.version,
    valid: report.valid,
    conflictFree: report.conflictFree,
    strongerProofComplete: report.strongerProofComplete,
    baseChecksum: report.baseChecksum,
    proofGeometry: report.proofGeometry,
    radialBoundModel: report.radialBoundModel,
    tolerance: report.tolerance,
    orthogonalityTolerance: report.orthogonalityTolerance,
    proofBudget: report.proofBudget,
    counts: report.counts,
    orthogonalProjectionRadialChecks: report.orthogonalProjectionRadialChecks,
    conflicts: report.conflicts,
    errors: report.errors
  };
  return crypto.createHash('sha256').update(JSON.stringify(basis)).digest('hex');
}

function analyze(world, constraints, options) {
  options = options || {};
  const base = BasePreflight.analyze(world, constraints, options.base || options);
  const orthogonalityTolerance = bounded(
    options.orthogonalityTolerance,
    0,
    MAX_ORTHOGONALITY_TOLERANCE,
    DEFAULT_ORTHOGONALITY_TOLERANCE
  );
  const projectionPairBudget = projectionPairCandidateBudget(options.maxProjectionPairCandidates);
  const tolerance = base.tolerance;
  const checks = [];
  const additionalConflicts = [];
  let projectionPairBuckets = 0;
  let projectionMetricRecords = 0;
  let projectionPairCandidatesAvailable = 0;
  let projectionPairCandidates = 0;
  let proofBudgetExhausted = false;
  let radialMaximumChecks = 0;
  let radialMaximumConflicts = 0;
  let radialMinimumChecks = 0;
  let radialMinimumConflicts = 0;

  if (base.valid) {
    const exact = ExactGeometry.analyze(world, constraints, { tolerance });
    const projections = (exact.groups || []).filter(group => !group.conflict);
    const radials = (exact.radialGroups || []).filter(group => !group.conflict);
    const projectionMetricsByPair = indexProjectionMetricsByPair(projections);
    projectionPairBuckets = projectionMetricsByPair.size;
    projectionMetricRecords = projections.length;
    projectionPairCandidatesAvailable = radials.reduce((total, radial) => {
      return total + candidatePairCount(projectionMetricsByPair.get(radial.key) || []);
    }, 0);

    radialLoop:
    for (const radial of radials) {
      const samePairMetrics = projectionMetricsByPair.get(radial.key) || [];
      for (let i = 0; i < samePairMetrics.length; i += 1) {
        for (let j = i + 1; j < samePairMetrics.length; j += 1) {
          if (projectionPairCandidates >= projectionPairBudget) {
            proofBudgetExhausted = projectionPairCandidates < projectionPairCandidatesAvailable;
            break radialLoop;
          }

          projectionPairCandidates += 1;
          const firstMetric = samePairMetrics[i];
          const secondMetric = samePairMetrics[j];
          const first = firstMetric.group;
          const second = secondMetric.group;
          if (firstMetric.unitError > orthogonalityTolerance) continue;
          if (secondMetric.unitError > orthogonalityTolerance) continue;
          if (Math.abs(dot(first.direction, second.direction)) > orthogonalityTolerance) continue;

          const singularValues = singularValueBounds(first.direction, second.direction);
          if (!(singularValues.min > Number.EPSILON) || !(singularValues.max > 0)) continue;

          const firstMinimum = firstMetric.minimumMagnitude;
          const secondMinimum = secondMetric.minimumMagnitude;
          const firstMaximum = firstMetric.maximumMagnitude;
          const secondMaximum = secondMetric.maximumMagnitude;
          const involved = [first, second, radial];
          const summary = {
            a: radial.a,
            b: radial.b,
            directions: [roundedDirection(first.direction), roundedDirection(second.direction)],
            projectionIntersections: [roundedInterval(first.intersection), roundedInterval(second.intersection)],
            distanceIntersection: roundedInterval(radial.intersection),
            minimumProjectionMagnitudes: [round(firstMinimum), round(secondMinimum)],
            maximumProjectionMagnitudes: [
              Number.isFinite(firstMaximum) ? round(firstMaximum) : firstMaximum,
              Number.isFinite(secondMaximum) ? round(secondMaximum) : secondMaximum
            ],
            orthogonalityDot: round(dot(first.direction, second.direction)),
            basisSingularValues: {
              min: round(singularValues.min),
              max: round(singularValues.max)
            },
            constraintIds: constraintIds(involved),
            families: families(involved),
            radialMaximumCheck: null,
            radialMinimumCheck: null
          };

          if (Number.isFinite(radial.intersection.max)) {
            const maximumAllowedDistance = radial.intersection.max;

            // The base preflight already proves either one-dimensional violation alone.
            // Skip those here so this layer reports only genuinely combined evidence.
            if (firstMinimum <= maximumAllowedDistance + tolerance &&
                secondMinimum <= maximumAllowedDistance + tolerance) {
              const projectionMagnitudeLowerBound = Math.hypot(firstMinimum, secondMinimum);
              const minimumRequiredDistance = projectionMagnitudeLowerBound / singularValues.max;
              const decisionWitness = radialMaximumWitness(
                projectionMagnitudeLowerBound,
                singularValues,
                minimumRequiredDistance,
                maximumAllowedDistance,
                tolerance
              );
              const conflict = minimumRequiredDistance > maximumAllowedDistance + tolerance;
              summary.radialMaximumCheck = {
                projectionMagnitudeLowerBound: round(projectionMagnitudeLowerBound),
                minimumRequiredDistance: round(minimumRequiredDistance),
                maximumAllowedDistance: round(maximumAllowedDistance),
                decisionWitness,
                conflict
              };
              radialMaximumChecks += 1;
              if (conflict) {
                radialMaximumConflicts += 1;
                additionalConflicts.push({
                  code: 'ORTHOGONAL_PROJECTIONS_EXCEED_DISTANCE_MAX',
                  a: summary.a,
                  b: summary.b,
                  directions: clone(summary.directions),
                  projectionIntersections: clone(summary.projectionIntersections),
                  distanceIntersection: clone(summary.distanceIntersection),
                  minimumProjectionMagnitudes: clone(summary.minimumProjectionMagnitudes),
                  basisSingularValues: clone(summary.basisSingularValues),
                  projectionMagnitudeLowerBound: round(projectionMagnitudeLowerBound),
                  minimumRequiredDistance: round(minimumRequiredDistance),
                  maximumAllowedDistance: round(maximumAllowedDistance),
                  decisionWitness: clone(decisionWitness),
                  orthogonalityDot: summary.orthogonalityDot,
                  constraintIds: clone(summary.constraintIds),
                  families: clone(summary.families)
                });
              }
            }
          }

          // For the accepted two-direction basis, exact singular values convert
          // projection-vector magnitude bounds into conservative radial bounds.
          // Exact orthonormal inputs have singular values 1 and reduce to hypot().
          if (Number.isFinite(radial.intersection.min) &&
              Number.isFinite(firstMaximum) && Number.isFinite(secondMaximum)) {
            const minimumAllowedDistance = radial.intersection.min;
            const projectionMagnitudeUpperBound = Math.hypot(firstMaximum, secondMaximum);
            const maximumPossibleDistance = projectionMagnitudeUpperBound / singularValues.min;
            const decisionWitness = radialMinimumWitness(
              minimumAllowedDistance,
              projectionMagnitudeUpperBound,
              singularValues,
              maximumPossibleDistance,
              tolerance
            );
            const conflict = minimumAllowedDistance > maximumPossibleDistance + tolerance;
            summary.radialMinimumCheck = {
              minimumAllowedDistance: round(minimumAllowedDistance),
              projectionMagnitudeUpperBound: round(projectionMagnitudeUpperBound),
              maximumPossibleDistance: round(maximumPossibleDistance),
              decisionWitness,
              conflict
            };
            radialMinimumChecks += 1;
            if (conflict) {
              radialMinimumConflicts += 1;
              additionalConflicts.push({
                code: 'DISTANCE_MIN_EXCEEDS_ORTHOGONAL_PROJECTION_MAX',
                a: summary.a,
                b: summary.b,
                directions: clone(summary.directions),
                projectionIntersections: clone(summary.projectionIntersections),
                distanceIntersection: clone(summary.distanceIntersection),
                maximumProjectionMagnitudes: clone(summary.maximumProjectionMagnitudes),
                basisSingularValues: clone(summary.basisSingularValues),
                projectionMagnitudeUpperBound: round(projectionMagnitudeUpperBound),
                maximumPossibleDistance: round(maximumPossibleDistance),
                minimumAllowedDistance: round(minimumAllowedDistance),
                decisionWitness: clone(decisionWitness),
                orthogonalityDot: summary.orthogonalityDot,
                constraintIds: clone(summary.constraintIds),
                families: clone(summary.families)
              });
            }
          }

          if (summary.radialMaximumCheck || summary.radialMinimumCheck) checks.push(summary);
        }
      }
    }
  }

  const strongerProofComplete = base.valid && !proofBudgetExhausted;
  const conflicts = (base.conflicts || []).map(clone).concat(additionalConflicts.map(clone));
  const report = {
    schema: REPORT_SCHEMA,
    version: VERSION,
    ok: base.valid && conflicts.length === 0 && strongerProofComplete,
    valid: base.valid,
    conflictFree: base.valid && conflicts.length === 0,
    strongerProofComplete,
    baseChecksum: base.checksum,
    proofGeometry: 'full-precision-normalized',
    radialBoundModel: 'singular-value-conservative',
    tolerance,
    orthogonalityTolerance,
    proofBudget: {
      maxProjectionPairCandidates: Number.isFinite(projectionPairBudget) ? projectionPairBudget : null,
      exhausted: proofBudgetExhausted
    },
    base: clone(base),
    counts: {
      baseConflicts: (base.conflicts || []).length,
      projectionPairBuckets,
      projectionMetricRecords,
      projectionPairCandidatesAvailable,
      projectionPairCandidates,
      orthogonalProjectionRadialChecks: checks.length,
      orthogonalProjectionRadialConflicts: additionalConflicts.length,
      radialMaximumChecks,
      radialMaximumConflicts,
      radialMinimumChecks,
      radialMinimumConflicts,
      conflicts: conflicts.length,
      unsupportedConstraints: base.counts ? base.counts.unsupportedConstraints : 0
    },
    orthogonalProjectionRadialChecks: checks,
    conflicts,
    errors: clone(base.errors || []),
    evidence: [
      checks.length + ' same-pair orthogonal two-projection/radial check pair(s) evaluated',
      projectionPairBuckets + ' same-pair projection bucket(s) indexed once and reused for radial lookup',
      projectionMetricRecords + ' projection metric record(s) computed once and reused across candidate pair checks',
      projectionPairCandidates + ' of ' + projectionPairCandidatesAvailable + ' same-pair projection pair candidate(s) evaluated before strict orthogonality filtering',
      proofBudgetExhausted
        ? 'Configured projection-pair proof budget was exhausted; stronger proof coverage is incomplete and cannot be treated as conflict-free evidence.'
        : 'Projection-pair proof budget did not truncate stronger proof coverage.',
      radialMaximumConflicts + ' combined projection-lower-bound/radial-maximum conflict(s) proven',
      radialMinimumConflicts + ' combined projection-upper-bound/radial-minimum conflict(s) proven',
      'Orthogonality and radial proof decisions use full-precision normalized geometry; 1e-9 rounding is presentation-only.',
      'Accepted two-direction bases use exact singular values to convert projection-vector magnitude bounds into conservative radial bounds; exact orthonormal inputs reduce to the prior Pythagorean result.',
      'Each combined radial proof carries an unrounded decisionWitness with projection magnitude bounds, basis singular values, compared radial values, proof margin and tolerance.',
      'Accepted directions must each be unit-length and mutually orthogonal within tolerance ' + orthogonalityTolerance,
      'The proof remains limited to one canonical body pair and exactly two accepted projection directions at a time.'
    ],
    limitations: [
      'This is an optional stronger layer over the existing conservative preflight; the base preflight and solver are unchanged.',
      'Projection groups are indexed by canonical body pair once per analysis; indexing changes lookup work only and does not widen proof eligibility or reorder same-pair groups.',
      'Unit-length error and projection interval magnitude bounds are computed once per non-conflicting projection group and reused across pair candidates; this is structural work reduction, not a benchmarked wall-clock claim.',
      'The optional maxProjectionPairCandidates budget bounds quadratic stronger-proof work deterministically; null means unbounded/default behavior, and exhaustion is exposed rather than silently treated as complete proof coverage.',
      'It combines exactly two same-body-pair projected intervals only when their full-precision normalized directions are unit-length and mutually orthogonal within the configured strict tolerance.',
      'Because eligibility allows a strict numeric tolerance, proof distances use conservative singular-value bounds rather than assuming an exactly orthonormal basis; this avoids tolerance-edge false conflicts.',
      'Rounded directions, intervals and summary distances in the public receipt are display evidence only; decisionWitness preserves the unrounded values used by each combined proof.',
      'It does not combine oblique or merely near-orthogonal directions, more than two projected directions at once, or constraints from different body pairs.',
      'A radial maximum can be checked from projection lower bounds; a radial minimum is checked only when both accepted projection intervals have finite upper magnitudes and the two-direction basis is non-singular.',
      'It does not prove global constraint satisfiability, convergence, stability or physical correctness and does not reason across triangles or loops.',
      'It is 2D game/prototype correctness evidence, not scientific validation or a 3D physics claim.'
    ]
  };
  report.checksum = reportChecksum(report);
  return report;
}

module.exports = {
  VERSION,
  REPORT_SCHEMA,
  DEFAULT_ORTHOGONALITY_TOLERANCE,
  MAX_ORTHOGONALITY_TOLERANCE,
  MAX_PROJECTION_PAIR_CANDIDATE_BUDGET,
  analyze
};
