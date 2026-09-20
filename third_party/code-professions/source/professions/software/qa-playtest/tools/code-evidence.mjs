import {data, exact, need, same, seal, bound} from '../../../../workflows/code/contract.mjs';

export function reviewCodeEvidence(inputBuild, inputObservations) {
  const build = data(inputBuild), observations = data(inputObservations);
  bound(build, 'buildSha256'); bound(build.plan, 'planSha256');
  need(Array.isArray(observations) && observations.length <= 4, 'OBSERVATION_COUNT_INVALID');
  const issues = [], seen = new Set(), byLanguage = new Map(), completeRuns = [];
  for (const observation of observations) {
    exact(observation, ['language', 'run', 'buildSha256', 'sourceSha256', 'runtime', 'status'], ['cases', 'diagnostic']);
    const target = build.targets.find(t => t.language === observation.language);
    need(target && [1, 2].includes(observation.run), 'OBSERVATION_TARGET_UNKNOWN');
    const key = observation.language + ':' + observation.run;
    need(!seen.has(key), 'OBSERVATION_DUPLICATE'); seen.add(key);
    need(observation.buildSha256 === build.buildSha256 && observation.sourceSha256 === target.sourceSha256, 'STALE_OBSERVATION');
    need(typeof observation.runtime === 'string' && observation.runtime.length > 0, 'RUNTIME_IDENTITY_REQUIRED');
    need(['COMPLETE', 'BLOCKED', 'FAILED'].includes(observation.status), 'OBSERVATION_STATUS_INVALID');
    if (observation.status !== 'COMPLETE') { issues.push({code: 'RUNTIME_' + observation.status, target: key, diagnostic: observation.diagnostic || ''}); continue; }
    need(Array.isArray(observation.cases) && observation.cases.length === build.plan.cases.length, 'CASE_EVIDENCE_INCOMPLETE');
    const rows = new Map();
    for (const row of observation.cases) {
      exact(row, ['id', 'inputUnchanged'], ['actual', 'error']);
      need(build.plan.cases.some(c => c.id === row.id) && !rows.has(row.id), 'CASE_EVIDENCE_DUPLICATE_OR_UNKNOWN');
      need(typeof row.inputUnchanged === 'boolean' && Object.hasOwn(row, 'actual') !== Object.hasOwn(row, 'error'), 'CASE_OBSERVATION_INVALID');
      if (Object.hasOwn(row, 'error')) need(typeof row.error === 'string', 'CASE_OBSERVATION_INVALID');
      rows.set(row.id, row);
    }
    for (const expected of build.plan.cases) {
      const row = rows.get(expected.id);
      const passes = Object.hasOwn(expected, 'error') ? row.error === expected.error : Object.hasOwn(row, 'actual') && same(row.actual, expected.expected);
      if (!passes) issues.push({code: 'CASE_MISMATCH', target: key, case: expected.id, expected: Object.hasOwn(expected, 'error') ? {error: expected.error} : {actual: expected.expected}, observed: row});
      if (!row.inputUnchanged) issues.push({code: 'INPUT_MUTATED', target: key, case: expected.id});
    }
    const ordered = build.plan.cases.map(c => rows.get(c.id));
    completeRuns.push({language: observation.language, rows: ordered});
    if (byLanguage.has(observation.language) && !same(byLanguage.get(observation.language), ordered)) issues.push({code: 'RUNTIME_NOT_REPEATABLE', target: observation.language});
    byLanguage.set(observation.language, ordered);
  }
  for (const target of build.targets) for (const run of [1, 2]) if (!seen.has(target.language + ':' + run)) issues.push({code: 'RUNTIME_NOT_RUN', target: target.language + ':' + run});
  if (completeRuns.some(a => completeRuns.some(b => a.language !== b.language && !same(a.rows, b.rows)))) issues.push({code: 'LANGUAGE_PARITY_MISMATCH'});
  const result = issues.length === 0 ? 'PASS' : issues.some(x => ['RUNTIME_NOT_RUN', 'RUNTIME_BLOCKED'].includes(x.code)) ? 'BLOCKED' : 'HOLD';
  return seal({schema: 'axm.code.qa.v1', buildSha256: build.buildSha256, result, issues, observations,
    requirementCoverage: build.plan.requirements.map(r => ({id: r.id, cases: r.cases, passed: result === 'PASS' || (observations.length === build.targets.length * 2 && observations.every(o => o.status === 'COMPLETE') && !issues.some(i => !i.case || r.cases.includes(i.case)))})),
    scope: 'Explicit acceptance cases, two fresh executions per requested language, input preservation and cross-language equality; no general correctness proof.'}, 'qaSha256');
}
