import {data, need, bound, seal} from '../../../../workflows/code/contract.mjs';

export function assessCodeReadiness(inputBuild, inputQa) {
  const build = data(inputBuild), qa = data(inputQa);
  bound(build, 'buildSha256'); bound(qa, 'qaSha256');
  need(qa.buildSha256 === build.buildSha256, 'QA_BUILD_MISMATCH');
  need(['PASS', 'HOLD', 'BLOCKED'].includes(qa.result), 'QA_RESULT_INVALID');
  return seal({schema: 'axm.code.readiness.v1', buildSha256: build.buildSha256, qaSha256: qa.qaSha256,
    result: qa.result === 'PASS' ? 'VERIFIED_FOR_CASES' : qa.result,
    scope: qa.scope, acceptanceAuthority: false, deployment: false, generalReleaseReadiness: false,
    remaining: ['Requirements remain caller-declared.', 'Case coverage is not branch coverage or specification completeness.', 'No application, deployment, security or performance assessment.']}, 'readinessSha256');
}
