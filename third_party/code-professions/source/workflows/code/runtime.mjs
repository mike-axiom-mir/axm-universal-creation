// Optional institutional executor. Invoke only with this workflow's freshly compiled build.
// This runs bounded generated modules; it is not an operating-system sandbox.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
export function createCodeExecutor({python = 'python3', timeout = 15000} = {}) {
  const env = Object.fromEntries(['PATH', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP'].filter(k => process.env[k] !== undefined).map(k => [k, process.env[k]]));
  return ({build, target, run}) => {
    const observation = {language: target.language, run, buildSha256: build.buildSha256, sourceSha256: target.sourceSha256,
      runtime: target.language === 'javascript' ? 'node:' + process.version : 'python:unobserved'};
    let folder;
    try {
      folder = fs.mkdtempSync(path.join(os.tmpdir(), 'axm-code-job-'));
      for (const artifact of target.artifacts) fs.writeFileSync(path.join(folder, artifact.path), artifact.content, {encoding: 'utf8', flag: 'wx'});
      fs.writeFileSync(path.join(folder, 'cases.json'), JSON.stringify(build.plan.cases));
      const js = target.language === 'javascript';
      const command = js ? process.execPath : python;
      const options = {cwd: folder, env, encoding: 'utf8', timeout, maxBuffer: 8 * 1048576, windowsHide: true};
      const syntaxArgs = js ? ['--check', 'module.js'] : ['-I', '-B', '-c', 'from pathlib import Path; compile(Path("module.py").read_text(encoding="utf-8"), "module.py", "exec")'];
      const syntax = spawnSync(command, syntaxArgs, options);
      if (syntax.error || syntax.status !== 0) return {...observation, status: syntax.error?.code === 'ENOENT' ? 'BLOCKED' : 'FAILED', diagnostic: 'SYNTAX_PROCESS:' + (syntax.error?.code || syntax.stderr.slice(0, 2000))};
      const harness = js ? 'observe-js.cjs' : 'observe-python.py';
      fs.copyFileSync(path.join(here, harness), path.join(folder, harness));
      const result = spawnSync(command, js ? [harness] : ['-I', '-B', harness], options);
      if (result.error || result.status !== 0) return {...observation, status: 'FAILED', diagnostic: 'RUNTIME_PROCESS:' + (result.error?.code || result.stderr.slice(0, 2000))};
      const observed = JSON.parse(result.stdout);
      return {...observation, status: 'COMPLETE', runtime: observed.runtime, cases: observed.cases};
    } catch (error) {
      return {...observation, status: 'FAILED', diagnostic: 'EXECUTOR_ERROR:' + String(error.message).slice(0, 2000)};
    } finally { if (folder) fs.rmSync(folder, {recursive: true, force: true}); }
  };
}
