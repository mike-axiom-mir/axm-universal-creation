import {data, need, digest, same, seal, bound} from '../../../../workflows/code/contract.mjs';

export function bindCodeBuild(inputPlan, inputPair) {
  const plan = data(inputPlan), pair = data(inputPair);
  bound(plan, 'planSha256'); bound(pair, 'compilationPairSha256');
  need(same(pair.first, pair.repeated), 'BUILD_NOT_REPRODUCIBLE');
  need(pair.first.length === plan.languages.length, 'BUILD_TARGETS_INCOMPLETE');
  const targets = pair.first.map((compiled, i) => {
    const language = plan.languages[i], ext = language === 'python' ? 'py' : 'js';
    bound(compiled, 'compilationSha256');
    need(compiled.languageId === language && same(compiled.exports, plan.program.exports), 'BUILD_CONTRACT_MISMATCH');
    need(compiled.programSha256 === digest(plan.program), 'BUILD_PROGRAM_MISMATCH');
    need(compiled.verification.executed === false && compiled.verification.emittedCases === plan.cases.length, 'BUILD_EVIDENCE_INVALID');
    need(compiled.artifacts.length === 2, 'BUILD_ARTIFACTS_INCOMPLETE');
    for (const [index, role] of ['source', 'verification'].entries()) {
      const artifact = compiled.artifacts[index];
      need(artifact.path === (index ? 'selftest.' : 'module.') + ext && artifact.role === role, 'BUILD_PATH_OR_ROLE_INVALID');
      need(typeof artifact.content === 'string' && Buffer.byteLength(artifact.content) <= 1048576 && artifact.sha256 === digest(artifact.content), 'BUILD_ARTIFACT_DIGEST_MISMATCH');
    }
    return {language, compilationSha256: compiled.compilationSha256, sourceSha256: compiled.artifacts[0].sha256, artifacts: compiled.artifacts,
      sourceMap: compiled.sourceMap, reusableFunctions: compiled.reusableFunctions};
  });
  return seal({schema: 'axm.code.build.v1', plan, compiler: pair.compiler, programSha256: digest(plan.program), targets,
    reproducibility: {buildsCompared: 2, identical: true}, execution: 'NOT_RUN'}, 'buildSha256');
}
