'use strict';

const crypto = require('crypto');
const BasePreflight = require('./uc-constraint-preflight.js');
const ExactGeometry = require('./uc-exact-projection-geometry.js');

const VERSION = '0.3.0';
const REPORT_SCHEMA = 'axm.uc-orthogonal-projection-preflight/v0.3';
const DEFAULT_ORTHOGONALITY_TOLERANCE = 1e-9;
const MAX_ORTHOGONALITY_TOLERANCE = 1e-6;

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

function isUnitDirection(direction, tolerance) {
  return Math.abs(directionNormSquared(direction) - 1) <= tolerance;
}

function samePair(left, right) {
  return left.a === right.a && left.b === right.b;
}

function constraintIds(groups) {
  return Array.from(new Set(groups.flatMap(group => (group.constraints || []).map(item => item.id)))).sort();
}

function families(groups) {
  return Array.from(new Set(groups.flatMap(group => (group.constraints || []).map(item => item.family)))).sort();
}

function reportChecksum(report) {
  const basis = {
    schema: report.schema,
    version: report.version,
    valid: report.valid,
    conflictFree: report.conflictFree,
    baseChecksum: report.baseChecksum,
    proofGeometry: report.proofGeometry,
    tolerance: report.tolerance,
    orthogonalityTolerance: report.orthogonalityTolerance,
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
  const tolerance = base.tolerance;
  const checks = [];
  const additionalConflicts = [];
  let radialMaximumChecks = 0;
  let radialMaximumConflicts = 0;
  let radialMinimumChecks = 0;
  let radialMinimumConflicts = 0;

  if (base.valid) {
    const exact = ExactGeometry.analyze(world, constraints, { tolerance });
    const projections = (exact.groups || []).filter(group => !group.conflict);
    const radials = (exact.radialGroups || []).filter(group => !group.conflict);

    radials.forEach(radial => {
      const samePairProjections = projections.filter(group => samePair(group, radial));
      for (let i = 0; i < samePairProjections.length; i += 1) {
        for (let j = i + 1; j < samePairProjections.length; j += 1) {
          const first = samePairProjections[i];
          const second = samePairProjections[j];
          if (!isUnitDirection(first.direction, orthogonalityTolerance)) continue;
          if (!isUnitDirection(second.direction, orthogonalityTolerance)) continue;
          if (Math.abs(dot(first.direction, second.direction)) > orthogonalityTolerance) continue;

          const firstMinimum = minimumAbsoluteInterval(first.intersection);
          const secondMinimum = minimumAbsoluteInterval(second.intersection);
          const firstMaximum = maximumAbsoluteInterval(first.intersection);
          const secondMaximum = maximumAbsoluteInterval(second.intersection);
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
              const minimumRequiredDistance = Math.hypot(firstMinimum, secondMinimum);
              const conflict = minimumRequiredDistance > maximumAllowedDistance + tolerance;
              summary.radialMaximumCheck = {
                minimumRequiredDistance: round(minimumRequiredDistance),
                maximumAllowedDistance: round(maximumAllowedDistance),
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
                  minimumRequiredDistance: round(minimumRequiredDistance),
                  maximumAllowedDistance: round(maximumAllowedDistance),
                  orthogonalityDot: summary.orthogonalityDot,
                  constraintIds: clone(summary.constraintIds),
                  families: clone(summary.families)
                });
              }
            }
          }

          // In 2D, two orthonormal projected coordinates fully determine the
          // displacement magnitude. If both projected intervals are bounded,
          // their largest possible magnitudes therefore give a safe radial
          // upper bound. A radial minimum above that bound is locally impossible.
          if (Number.isFinite(radial.intersection.min) &&
              Number.isFinite(firstMaximum) && Number.isFinite(secondMaximum)) {
            const minimumAllowedDistance = radial.intersection.min;
            const maximumPossibleDistance = Math.hypot(firstMaximum, secondMaximum);
            const conflict = minimumAllowedDistance > maximumPossibleDistance + tolerance;
            summary.radialMinimumCheck = {
              minimumAllowedDistance: round(minimumAllowedDistance),
              maximumPossibleDistance: round(maximumPossibleDistance),
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
                maximumPossibleDistance: round(maximumPossibleDistance),
                minimumAllowedDistance: round(minimumAllowedDistance),
                orthogonalityDot: summary.orthogonalityDot,
                constraintIds: clone(summary.constraintIds),
                families: clone(summary.families)
              });
            }
          }

          if (summary.radialMaximumCheck || summary.radialMinimumCheck) checks.push(summary);
        }
      }
    });
  }

  const conflicts = (base.conflicts || []).map(clone).concat(additionalConflicts.map(clone));
  const report = {
    schema: REPORT_SCHEMA,
    version: VERSION,
    ok: base.valid && conflicts.length === 0,
    valid: base.valid,
    conflictFree: base.valid && conflicts.length === 0,
    baseChecksum: base.checksum,
    proofGeometry: 'full-precision-normalized',
    tolerance,
    orthogonalityTolerance,
    base: clone(base),
    counts: {
      baseConflicts: (base.conflicts || []).length,
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
      radialMaximumConflicts + ' combined projection-lower-bound/radial-maximum conflict(s) proven',
      radialMinimumConflicts + ' combined projection-upper-bound/radial-minimum conflict(s) proven',
      'Orthogonality and radial proof decisions use full-precision normalized geometry; 1e-9 rounding is presentation-only.',
      'Accepted directions must each be unit-length and mutually orthogonal within tolerance ' + orthogonalityTolerance,
      'The proof uses the 2D orthonormal identity distance^2 = projectionA^2 + projectionB^2 only for one exact body pair.'
    ],
    limitations: [
      'This is an optional stronger layer over the existing conservative preflight; the base preflight and solver are unchanged.',
      'It combines exactly two same-body-pair projected intervals only when their full-precision normalized directions are unit-length and mutually orthogonal within the configured strict tolerance.',
      'Rounded directions and intervals in the public receipt are display evidence only and are never used to decide orthogonality or conflict.',
      'It does not combine oblique or merely near-orthogonal directions, more than two projected directions at once, or constraints from different body pairs.',
      'A radial maximum can be checked from projection lower bounds; a radial minimum is checked only when both orthogonal projection intervals have finite upper magnitudes.',
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
  analyze
};
