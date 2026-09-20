import {data, exact, need} from './contract.mjs';
import {planCodeJob} from '../../professions/software/software-architect/tools/code-plan.mjs';
import {resolveCodeJob, compileCodePlan} from '../../professions/software/developer-tools-engineer/tools/code-compiler.mjs';
import {bindCodeBuild} from '../../professions/software/build-engineer/tools/code-build.mjs';
import {reviewCodeEvidence} from '../../professions/software/qa-playtest/tools/code-evidence.mjs';
import {assessCodeReadiness} from '../../professions/software/integration-release/tools/code-readiness.mjs';
import {retainCodeConstruction} from '../../professions/software/software-maintainer/tools/code-retention.mjs';

export const STATIONS = Object.freeze([
  {id: 'contract', profession: 'software-architect', export: 'code-plan'},
  {id: 'compile', profession: 'developer-tools-engineer', export: 'code-compiler'},
  {id: 'build', profession: 'build-engineer', export: 'code-build'},
  {id: 'verify', profession: 'software-qa-playtest', export: 'code-evidence'},
  {id: 'readiness', profession: 'integration-release-engineer', export: 'code-readiness'},
  {id: 'retain', profession: 'software-maintainer', export: 'code-retention'}
]);

// The institution supplies pinned compiler and process capabilities. JSON never supplies code or executable paths.
export function runCodeWorkflow(input, {compiler, compilerIdentity, execute} = {}) {
  const stations = [];
  try {
    const request = data(input);
    exact(request, ['action'], ['job', 'archive']);
    if (request.action === 'catalog') {
      exact(request, ['action']);
      return {schema: 'axm.code.workflow-catalog.v1', status: 'EXPERIMENTAL', stations: STATIONS, compiler: compiler.catalog(), actions: ['catalog', 'build', 'verify', 'retain'], noModelRequired: true};
    }
    need(['build', 'verify', 'retain'].includes(request.action), 'ACTION_UNKNOWN');
    exact(request, ['action', 'job'], request.action === 'retain' ? ['archive'] : []);
    const plan = planCodeJob(resolveCodeJob(request.job, compiler));
    stations.push({id: 'contract', result: 'CONTRACT_READY', planSha256: plan.planSha256});
    const pair = compileCodePlan(plan, compiler, compilerIdentity);
    stations.push({id: 'compile', result: 'SOURCE_GENERATED'});
    const build = bindCodeBuild(plan, pair);
    stations.push({id: 'build', result: 'REPRODUCIBLE', buildSha256: build.buildSha256});
    if (request.action === 'build') return {schema: 'axm.code.workflow.v1', result: 'CANDIDATE', stations, build, qa: null, readiness: null, retention: null};
    const observations = [];
    if (execute) for (const target of build.targets) for (const run of [1, 2]) {
      observations.push(execute({build, target, run}));
    }
    const qa = reviewCodeEvidence(build, observations);
    stations.push({id: 'verify', result: qa.result});
    const readiness = assessCodeReadiness(build, qa);
    stations.push({id: 'readiness', result: readiness.result});
    let retention = null;
    if (request.action === 'retain' && qa.result === 'PASS') {
      retention = retainCodeConstruction(compiler, build, readiness, request.archive);
      stations.push({id: 'retain', result: 'CONSTRUCTION_RETAINED'});
    }
    return {schema: 'axm.code.workflow.v1', result: readiness.result, stations, build, qa, readiness, retention};
  } catch (error) { return {schema: 'axm.code.workflow.v1', result: 'HOLD', stations, diagnostic: String(error.message)}; }
}
