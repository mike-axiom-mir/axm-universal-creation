import {data, exact, need, id, canonical, seal} from '../../../../workflows/code/contract.mjs';

// Requirements are explicit contracts, never inferred from prose or a role name.
export function planCodeJob(input) {
  const job = data(input);
  exact(job, ['id', 'program', 'cases', 'requirements', 'languages', 'source']);
  need(id(job.id), 'JOB_ID_INVALID');
  need(Array.isArray(job.languages) && job.languages.length > 0 && job.languages.length <= 2, 'LANGUAGES_REQUIRED');
  need(new Set(job.languages).size === job.languages.length && job.languages.every(x => ['javascript', 'python'].includes(x)), 'LANGUAGE_UNSUPPORTED');
  job.languages.sort();
  need(Array.isArray(job.program?.functions) && Array.isArray(job.program?.exports), 'PROGRAM_REQUIRED');
  need(Array.isArray(job.cases) && job.cases.length > 0 && job.cases.length <= 256, 'ACCEPTANCE_CASES_REQUIRED');
  need(Array.isArray(job.requirements) && job.requirements.length > 0 && job.requirements.length <= 128, 'REQUIREMENTS_REQUIRED');
  const caseIds = new Set(), calls = new Map();
  for (const row of job.cases) {
    exact(row, ['id', 'function', 'args'], ['expected', 'error']);
    need(id(row.id) && !caseIds.has(row.id), 'CASE_ID_INVALID_OR_DUPLICATE'); caseIds.add(row.id);
    need(job.program.exports.includes(row.function) && Array.isArray(row.args), 'CASE_EXPORT_INVALID');
    need(Object.hasOwn(row, 'expected') !== Object.hasOwn(row, 'error'), 'CASE_ORACLE_REQUIRED');
    if (Object.hasOwn(row, 'error')) need(typeof row.error === 'string' && /^[A-Z_]{1,80}$/.test(row.error), 'CASE_ERROR_INVALID');
    const call = canonical([row.function, row.args]), oracle = canonical(Object.hasOwn(row, 'expected') ? {expected: row.expected} : {error: row.error});
    need(!calls.has(call) || calls.get(call) === oracle, 'CONFLICTING_EXPECTATIONS'); calls.set(call, oracle);
  }
  const requirementIds = new Set(), assigned = new Set();
  for (const requirement of job.requirements) {
    exact(requirement, ['id', 'statement', 'cases']);
    need(id(requirement.id) && !requirementIds.has(requirement.id), 'REQUIREMENT_ID_INVALID_OR_DUPLICATE'); requirementIds.add(requirement.id);
    need(typeof requirement.statement === 'string' && requirement.statement.trim().length > 0 && requirement.statement.length <= 2000, 'REQUIREMENT_STATEMENT_REQUIRED');
    need(Array.isArray(requirement.cases) && requirement.cases.length > 0 && new Set(requirement.cases).size === requirement.cases.length, 'REQUIREMENT_CASES_REQUIRED');
    for (const name of requirement.cases) { need(caseIds.has(name), 'REQUIREMENT_CASE_UNKNOWN'); assigned.add(name); }
    requirement.cases.sort();
  }
  need(assigned.size === caseIds.size, 'UNASSIGNED_CASE');
  for (const name of job.program.exports) need(job.cases.some(c => c.function === name && Object.hasOwn(c, 'expected')), 'EXPORT_SUCCESS_CASE_MISSING:' + name);
  // A retained program must not smuggle unrelated, unexercised helper functions.
  const functions = new Map(job.program.functions.map(f => [f.name, f])), reached = new Set();
  function visit(name) {
    if (reached.has(name)) return;
    need(functions.has(name), 'FUNCTION_UNKNOWN'); reached.add(name);
    function walk(node) {
      if (!node || typeof node !== 'object') return;
      if (node.op === 'call') visit(node.function);
      for (const value of Object.values(node)) walk(value);
    }
    walk(functions.get(name).body);
  }
  job.program.exports.forEach(visit);
  need(reached.size === functions.size, 'UNREACHABLE_FUNCTION');
  const compare = (a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  job.cases.sort(compare);
  job.requirements.sort(compare);
  return seal({schema: 'axm.code.job-plan.v1', ...job, coverage: {exports: job.program.exports, cases: job.cases.length, requirements: job.requirements.length}}, 'planSha256');
}
