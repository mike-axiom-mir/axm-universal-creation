"""Pinned offline Grammar 102 / Glass process adapters. No caller code execution."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile


def run_grammar_tool(root, operation, request):
    if operation not in ('grammar-capsule','state-ripple','render-budget'):
        raise ValueError('unknown grammar tool')
    body=json.dumps(request,allow_nan=False).encode()
    if len(body)>1048576:raise ValueError('request exceeds 1 MiB')
    node=shutil.which('node')
    if not node:raise ValueError('Node.js is required for the grammar workbench')
    folder=Path(root)/'third_party/grammar-workbench'
    provenance=json.loads((folder/'provenance.json').read_text())
    names={'grammar-102.tgz'} if operation=='grammar-capsule' else {'state-ripple-core.js','construction-program-core.js','playground-core.js','render-budget-core.js'}
    for name in names:
        record=next(p for p in provenance if p['destination']==name)
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('pinned donor digest mismatch: '+name)
    with tempfile.TemporaryDirectory(prefix='axm-grammar-') as temp:
        if operation=='grammar-capsule':
            # Extract only ordinary package files after validating the complete archive.
            with tarfile.open(folder/'grammar-102.tgz','r:gz') as archive:
                members=archive.getmembers()
                if len(members)>2000 or sum(m.size for m in members)>32*1024*1024:
                    raise ValueError('grammar archive exceeds package bounds')
                for m in members:
                    p=PurePosixPath(m.name)
                    if not m.isfile() or p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='package':
                        raise ValueError('unsafe grammar archive member')
                for m in members:
                    p=Path(temp)/m.name;p.parent.mkdir(parents=True,exist_ok=True)
                    p.write_bytes(archive.extractfile(m).read())
            command=[node,str(Path(temp)/'package/bin/axm-grammar-capabilities.js')]
        else:command=[node,str(folder.resolve()/'run-glass.js'),operation]
        try:
            r=subprocess.run(command,input=body,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)
        except subprocess.TimeoutExpired as exc:raise ValueError('grammar tool exceeded 30 seconds') from exc
        if r.returncode:raise ValueError(r.stderr.decode(errors='replace')[:4000])
        return json.loads(r.stdout)
