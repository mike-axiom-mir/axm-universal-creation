// UC adapter; fabric.mjs is the unchanged pinned Apache-2.0 donor.
import { readFile, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { ParallelCapabilityFabric } from './fabric.mjs';

const [jobFile, receiptFile] = process.argv.slice(2);
const job = JSON.parse(await readFile(jobFile, 'utf8'));
if (Number(process.versions.node.split('.')[0]) < 20) throw Error('Node 20+ required');
const children = new Set();
let session;
function stop() { session?.cancel(); }
process.on('SIGTERM', stop);
process.on('SIGINT', stop);

function worker(task, signal) {
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();
    const child = spawn(job.python, ['-m', 'axm_uc.parallel_create', '--worker', task.input],
      { cwd: job.root, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] });
    children.add(child);
    let output = '', errors = '', failure;
    const kill = reason => { failure ??= reason; child.kill('SIGKILL'); };
    const abort = () => kill(Error('creation cancelled'));
    signal.addEventListener('abort', abort, { once: true });
    if (signal.aborted) abort();
    const timer = setTimeout(() => kill(Error('creation task timeout')), job.timeout * 1000);
    child.stdout.on('data', data => {
      if (output.length + data.length > 65536) kill(Error('worker output exceeds 64 KiB'));
      else output += data;
    });
    child.stderr.on('data', data => {
      if (errors.length + data.length > 65536) kill(Error('worker errors exceed 64 KiB'));
      else errors += data;
    });
    child.on('error', error => { failure = error; });
    child.on('close', code => {
      clearTimeout(timer); signal.removeEventListener('abort', abort); children.delete(child);
      if (failure || code !== 0) return reject(failure || Error(errors || `worker exit ${code}`));
      try { resolve({ output: { ...JSON.parse(output), processStartedMs: startedAt,
        processFinishedMs: Date.now() } }); } catch (error) { reject(error); }
    });
  });
}

try {
  const fabric = new ParallelCapabilityFabric({ limits: { workers: job.workers } });
  session = fabric.start({ runId: job.digest, goal: 'Build saved creative parts and assemble exact dependencies',
    stateRef: job.digest, tasks: job.tasks.map(task => ({ taskId: task.id,
      capabilityId: task.operation, dependencies: task.dependencies,
      authority: ['WRITE-SANDBOX'], resources: { workers: 1 }, inputRefs: [task.digest],
      run: ({ signal }) => worker(task, signal) })) });
  await writeFile(receiptFile, JSON.stringify(await session.result, null, 2));
} finally {
  for (const child of children) child.kill('SIGKILL');
  process.removeListener('SIGTERM', stop); process.removeListener('SIGINT', stop);
}
