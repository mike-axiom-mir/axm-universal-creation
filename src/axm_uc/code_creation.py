"""Create ordinary projects from explicit, reproducibly compiled code contracts."""
from __future__ import annotations

import json
from pathlib import Path

from .grammar_workbench import run_grammar_tool


def create_code_project(root: Path, inputs: dict) -> dict:
    # Use the established project writer and its protection of existing projects.
    from .capabilities import CapabilityError, builtin_write_project

    if not isinstance(inputs, dict) or set(inputs) != {'path', 'request'}:
        raise CapabilityError('code-program-project requires exactly path and request')
    if not isinstance(inputs['path'], str) or not inputs['path'].strip():
        raise CapabilityError('code project path must be a nonempty string')
    request = inputs['request']
    if not isinstance(request, dict) or request.get('action') not in ('build', 'verify', 'retain'):
        raise CapabilityError('code project action must be build, verify or retain')
    try:
        workflow = run_grammar_tool(root, 'code-workflow', request)
    except (ValueError, OSError) as exc:
        raise CapabilityError(str(exc)) from exc
    if workflow['result'] not in ('CANDIDATE', 'VERIFIED_FOR_CASES'):
        raise CapabilityError('code workflow did not produce an accepted project candidate', {'workflow': workflow})

    def json_text(value):
        return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + '\n'

    build = workflow['build']
    files = {
        'request.json': json_text(request),
        'construction.json': json_text(build['plan']),
        'workflow.json': json_text(workflow),
        'README.md': _project_readme(build, workflow['result']),
        'LICENSE-MPL-2.0.txt': (Path(root) / 'third_party/code-professions/source/LICENSE').read_text(encoding='utf-8'),
        'NOTICE.txt': 'Generated using AXM Grammar 102 with its embedded bounded runtime.\n'
                      'Grammar source: ' + build['compiler']['repository'] + ' @ ' + build['compiler']['commit'] + '\n'
                      'Profession source: ' + workflow['professionDonor']['repository'] + ' @ ' + workflow['professionDonor']['commit'] + '\n'
                      'Copyright 2026 Mike - Axiom/Mir. Source licenses and provenance remain attached.\n',
    }
    for target in build['targets']:
        for artifact in target['artifacts']:
            files[target['language'] + '/' + artifact['path']] = artifact['content']
    if workflow['retention'] is not None:
        files['archive.json'] = json_text(workflow['retention']['archive'])
        files['retention.json'] = json_text(workflow['retention'])
    result = builtin_write_project(root, {'path': inputs['path'], 'files': files, 'project_type': 'generic',
                                         'publish_mode': 'validated', 'replace': False})
    result['code_workflow'] = {
        'result': workflow['result'], 'buildSha256': build['buildSha256'],
        'stations': workflow['stations'], 'languages': build['plan']['languages'],
        'caseCount': len(build['plan']['cases']), 'requirementCount': len(build['plan']['requirements']),
        'archiveWritten': workflow['retention'] is not None,
        'runtimeEvidence': 'workflow.json', 'construction': 'construction.json',
    }
    return result


def _project_readme(build, status):
    commands = []
    if 'javascript' in build['plan']['languages']:
        commands.append('node javascript/selftest.js')
    if 'python' in build['plan']['languages']:
        commands.append('python python/selftest.py')
    return ('# ' + build['plan']['id'] + '\n\n'
            'Creation result: `' + status + '`. These are standalone typed pure-function modules.\n'
            'JavaScript exposes CommonJS exports; Python exposes named functions and `FUNCTIONS`.\n\n'
            '```sh\n' + '\n'.join(commands) + '\n```\n\n'
            '`request.json` retains the creation request. `construction.json` retains the normalized\n'
            'program, requirements and cases; `workflow.json` retains exact source and runtime evidence.\n'
            'If retention was requested, `archive.json` carries reusable function dependency closures.\n'
            'Restore with UC `code-program` action `restore`, then verify against the next job contract.\n\n'
            'Passing cases is bounded evidence, not correctness for all inputs or a complete application.\n'
            'Generated source is a realization; keep construction data when changing or reusing it.\n')
