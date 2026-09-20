import {data, exact, need, seal} from '../../../../workflows/code/contract.mjs';

export function resolveCodeJob(input, compiler) {
  const job = data(input);
  exact(job, ['id'], ['program', 'recipeId', 'languages', 'cases', 'requirements']);
  need(Object.hasOwn(job, 'program') !== Object.hasOwn(job, 'recipeId'), 'ONE_SOURCE_REQUIRED');
  let program = job.program, source = {kind: 'explicit-program'}, cases = job.cases, requirements = job.requirements;
  if (Object.hasOwn(job, 'recipeId')) {
    const recipe = compiler.getRecipe(job.recipeId);
    program = recipe.program;
    const bundled = recipe.cases.map((row, i) => ({id: 'recipe-' + String(i + 1).padStart(3, '0'), ...row}));
    cases = [...bundled, ...(cases || [])];
    requirements = [{id: 'recipe-contract', statement: recipe.description, cases: bundled.map(c => c.id)}, ...(requirements || [])];
    source = {kind: 'bundled-recipe', recipeId: job.recipeId};
  }
  const checked = compiler.validate(program);
  need(checked.result === 'CODE_PROGRAM_TYPECHECKED', 'PROGRAM_HELD:' + checked.errorCode);
  return {id: job.id, program: checked.program, cases, requirements, languages: job.languages || ['javascript', 'python'], source};
}

export function compileCodePlan(plan, compiler, identity) {
  exact(identity, ['repository', 'commit']);
  need(typeof identity.repository === 'string' && /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(identity.repository) && /^[a-f0-9]{40}$/.test(identity.commit), 'COMPILER_IDENTITY_REQUIRED');
  const cases = plan.cases.map(({id: ignored, ...row}) => row);
  const compile = () => plan.languages.map(languageId => {
    const result = compiler.compile({program: plan.program, languageId, cases});
    need(result.result === 'CODE_PROGRAM_CANDIDATE_READY', 'COMPILATION_HELD:' + result.errorCode);
    return result;
  });
  return seal({compiler: data(identity), first: compile(), repeated: compile()}, 'compilationPairSha256');
}
