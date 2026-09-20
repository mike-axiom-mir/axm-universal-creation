"""Pinned offline Grammar adapters and explicit bounded code-workflow execution."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile


OPERATIONS = ('grammar-capsule', 'state-ripple', 'render-budget', 'construction-program', 'code-program', 'code-workflow')


def _profession_donor(root):
    folder = Path(root) / 'third_party/code-professions'
    provenance = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))
    seen = set()
    for record in provenance['files']:
        relative = PurePosixPath(record['path'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in record['path'] or str(relative) in seen:
            raise ValueError('unsafe profession donor path')
        seen.add(str(relative))
        source = folder / 'source' / relative
        if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('pinned profession donor digest mismatch: ' + str(relative))
    return (folder / 'source').resolve(), provenance


def run_grammar_tool(root, operation, request):
    if operation not in OPERATIONS:
        raise ValueError('unknown grammar tool')
    body=json.dumps(request,allow_nan=False).encode()
    if len(body)>1048576:raise ValueError('request exceeds 1 MiB')
    node=shutil.which('node')
    if not node:raise ValueError('Node.js is required for the grammar workbench')
    folder=Path(root)/'third_party/grammar-workbench'
    provenance=json.loads((folder/'provenance.json').read_text())
    grammar_operation = operation in ('grammar-capsule', 'code-program', 'code-workflow')
    names={'grammar-102.tgz'} if grammar_operation else {'state-ripple-core.js','construction-program-core.js','playground-core.js','render-budget-core.js'}
    for name in names:
        record=next(p for p in provenance if p['destination']==name)
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('pinned donor digest mismatch: '+name)
    with tempfile.TemporaryDirectory(prefix='axm-grammar-') as temp:
        if grammar_operation:
            # Extract only ordinary package files after validating the complete archive.
            with tarfile.open(folder/'grammar-102.tgz','r:gz') as archive:
                members=archive.getmembers()
                if len(members)>2000 or sum(m.size for m in members)>32*1024*1024:
                    raise ValueError('grammar archive exceeds package bounds')
                seen = set()
                for m in members:
                    p=PurePosixPath(m.name)
                    if not m.isfile() or p.is_absolute() or '..' in p.parts or '\\' in m.name or not p.parts or p.parts[0]!='package' or p.as_posix() in seen:
                        raise ValueError('unsafe grammar archive member')
                    seen.add(p.as_posix())
                for m in members:
                    p=Path(temp)/m.name;p.parent.mkdir(parents=True,exist_ok=True)
                    p.write_bytes(archive.extractfile(m).read())
            package = Path(temp) / 'package'
            if operation == 'code-workflow':
                professionals, professional_pin = _profession_donor(root)
                compiler_pin = next(p for p in provenance if p['destination'] == 'grammar-102.tgz')
                identities = {
                    'compiler': {'repository': 'mike-axiom-mir/axm-102-grammer', 'commit': compiler_pin['commit']},
                    'professionals': {k: professional_pin[k] for k in ('repository', 'commit')},
                }
                command = [node, str(folder.resolve() / 'run-code-workflow.mjs'), str(package),
                           str(professionals), sys.executable, json.dumps(identities)]
            else:
                entry = 'axm-code-program.js' if operation == 'code-program' else 'axm-grammar-capabilities.js'
                command = [node, str(package / 'bin' / entry)]
        else:command=[node,str(folder.resolve()/'run-glass.js'),operation]
        timeout = 150 if operation == 'code-workflow' else 30
        try:
            r=subprocess.run(command,input=body,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
        except subprocess.TimeoutExpired as exc:raise ValueError(f'grammar tool exceeded {timeout} seconds') from exc
        if r.returncode:raise ValueError(r.stderr.decode(errors='replace')[:4000])
        if len(r.stdout) > 16 * 1048576: raise ValueError('grammar result exceeds 16 MiB')
        return json.loads(r.stdout)
