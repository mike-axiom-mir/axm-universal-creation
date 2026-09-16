'use strict';

const crypto = require('crypto');
const BasePreflight = require('./uc-constraint-preflight.js');

const VERSION = '0.1.0';
const REPORT_SCHEMA = 'axm.uc-orthogonal-projection-preflight/v0.1';
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

function minimumAbsoluteInterval(interval) {
  if (interval.min <= 0 && interval.max >= 0) return 0;
  return Math.min(Math.abs(interval.min), Math.abs(interval.max));
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

  if (base.valid) {
    const projections = (base.groups || []).filter(group => !group.conflict);
    const radials = (base.radialGroups || []).filter(group => !group.conflict && Number.isFinite(group.intersection.max));

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
          const maximumAllowedDistance = radial.intersection.max;

          // The base preflight already proves either one-dimensional violation alone.
          // Skip those here so this layer reports only genuinely combined evidence.
          if (firstMinimum > maximumAllowedDistance + tolerance) continue;
          if (secondMinimum > maximumAllowedDistance + tolerance) continue;

          const minimumRequiredDistance = Math.hypot(firstMinimum, secondMinimum);
          const conflict = minimumRequiredDistance > maximumAllowedDistance + tolerance;
          const involved = [first, second, radial];
          const summary = {
            a: radial.a,
            b: radial.b,
            directions: [clone(first.direction), clone(second.direction)],
            projectionIntersections: [clone(first.intersection), clone(second.intersection)],
            distanceIntersection: clone(radial.intersection),
            minimumProjectionMagnitudes: [round(firstMinimum), round(secondMinimum)],
            minimumRequiredDistance: round(minimumRequiredDistance),
            maximumAllowedDistance: round(maximumAllowedDistance),
            orthogonalityDot: round(dot(first.direction, second.direction)),
            conflict,
            constraintIds: constraintIds(involved),
            families: families(involved)
          };
          checks.push(summary);
          if (conflict) {
            additionalConflicts.push(Object.assign({
              code: 'ORTHOGONAL_PROJECTIONS_EXCEED_DISTANCE_MAX'
            }, clone(summary)));
          }
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
    tolerance,
    orthogonalityTolerance,
    base: clone(base),
    counts: {
      baseConflicts: (base.conflicts || []).length,
      orthogonalProjectionRadialChecks: checks.length,
      orthogonalProjectionRadialConflicts: additionalConflicts.length,
      conflicts: conflicts.length,
      unsupportedConstraints: base.counts ? base.counts.unsupportedConstraints : 0
    },
    orthogonalProjectionRadialChecks: checks,
    conflicts,
    errors: clone(base.errors || []),
    evidence: [
      checks.length + ' same-pair orthogonal two-projection/radial upper-bound check(s) evaluated',
      additionalConflicts.length + ' additional bounded orthogonal projection conflict(s) proven',
      'Accepted directions must each be unit-length and mutually orthogonal within tolerance ' + orthogonalityTolerance,
      'The proof uses the 2D orthonormal identity distance^2 = projectionA^2 + projectionB^2 only for one exact body pair.'
    ],
    limitations: [
      'This is an optional stronger layer over the existing conservative preflight; the base preflight and solver are unchanged.',
      'It combines exactly two same-body-pair projected intervals only when their normalized directions are unit-length and mutually orthogonal within the configured strict tolerance.',
      'It does not combine oblique or merely near-orthogonal directions, more than two projected directions, or constraints from different body pairs.',
      'It uses only a finite radial maximum. A radial minimum is not treated as contradictory because remaining geometric freedom may satisfy it.',
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
