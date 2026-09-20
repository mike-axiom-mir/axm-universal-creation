// Local UC adapter. JSON is data; executable capabilities come from bundled sources.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';

try {
  const [grammarRoot, professionRoot, python, identityJson] = process.argv.slice(2);
  const identities = JSON.parse(identityJson);
  const body = fs.readFileSync(0);
  if (body.length > 1048576) throw Error('REQUEST_BYTES_LIMIT');
  const compiler = createRequire(import.meta.url)(path.join(grammarRoot, 'code-programs/index.js'));
  const {runCodeWorkflow} = await import(pathToFileURL(path.join(professionRoot, 'workflows/code/index.mjs')));
  const {createCodeExecutor} = await import(pathToFileURL(path.join(professionRoot, 'workflows/code/runtime.mjs')));
  const result = runCodeWorkflow(JSON.parse(body), {
    compiler, compilerIdentity: identities.compiler, execute: createCodeExecutor({python}),
  });
  const output = JSON.stringify({...result, professionDonor: identities.professionals});
  if (Buffer.byteLength(output) > 16 * 1048576) throw Error('RESULT_BYTES_LIMIT');
  process.stdout.write(output + '\n');
} catch (error) {
  process.stderr.write(JSON.stringify({result: 'HOLD', diagnostic: String(error.message)}) + '\n');
  process.exitCode = 2;
}
