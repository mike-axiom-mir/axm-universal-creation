import {data, need, bound, seal} from '../../../../workflows/code/contract.mjs';

export function retainCodeConstruction(compiler, inputBuild, inputReadiness, archive) {
  const build = data(inputBuild), readiness = data(inputReadiness);
  bound(build, 'buildSha256'); bound(readiness, 'readinessSha256');
  need(readiness.buildSha256 === build.buildSha256 && readiness.result === 'VERIFIED_FOR_CASES', 'RETENTION_REQUIRES_VERIFIED_CASES');
  const capture = compiler.remember({program: build.plan.program, ...(archive === undefined ? {} : {archive: data(archive)}), origin: 'code-job:' + build.plan.id + ':' + build.buildSha256});
  return seal({schema: 'axm.code.retention.v1', archive: capture.archive, captured: capture.captured,
    construction: {plan: build.plan, compiler: build.compiler, buildSha256: build.buildSha256, readiness},
    truth: {explicitRetentionRequested: true, archivePersisted: false, canonicalPromotion: false, structuralDeduplication: true, helperBranchCoverageProven: false}}, 'retentionSha256');
}
