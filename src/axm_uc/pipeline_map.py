"""Read-only capability connections grounded in the current local catalog."""
from __future__ import annotations
import ast
from collections import deque
import hashlib
import json
from pathlib import Path

from .capabilities import CapabilityStore
from .donor_pipeline import build_pipeline_graph, path_status, pipeline_id
from .organ_library import ExecutableOrganLibrary

# Explicit source-backed adapters, not signatures inferred from function names.
REQUEST_BUILDERS = (
    ('metal', 'src/axm_uc/media_workbench.py', 'metal_request', 'Painted metal maps'),
    ('bitmap-label', 'src/axm_uc/media_workbench.py', 'label_request', 'Transparent bitmap labels'),
    ('normalize-wav', 'src/axm_uc/media_workbench.py', 'wav_request', 'PCM WAV normalization'),
    ('fabric', 'src/axm_uc/fabric_material.py', 'fabric_request', 'Woven fabric maps'),
    ('rts-reference-pack', 'src/axm_uc/rts_foundry.py', 'reference_pack_request', '83 authored RTS reference designs: articulated GLBs, detail levels, collision proxies and offline viewer'),
    ('survivor-workshop', 'src/axm_uc/workshop_project.py', 'workshop_request', 'Authored survivor workshop: verified surface GLBs and offline preview'),
)
BOUNDARY = 'Read-only candidate connections. No pipeline execution, compatibility proof, installation or automatic adoption.'


def _bounded(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer from {low} to {high}')


def installed_nodes(root):
    root=Path(root).resolve();nodes=[];sources={};excluded=[]
    def source_digest(path):
        p=(root/path).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            return False
        sources[path]=hashlib.sha256(p.read_bytes()).hexdigest();return True
    for cap in CapabilityStore(root).live():
        if cap.get('status') != 'live':continue
        declared_source=cap.get('implementation',{}).get('source')
        if isinstance(declared_source,str):source_digest(declared_source)
        nodes.append({'id':cap['id'], 'module':'capability', 'description':cap.get('purpose'),
                      'source':{'manifest_id':cap['id'],'version':cap.get('version'),
                                'manifest_sha256':hashlib.sha256(json.dumps(cap,sort_keys=True).encode()).hexdigest(),
                                'implementation':cap.get('implementation',{})},
                      'accepts':['request.kind.'+h for h in cap.get('handles',[])],
                      'provides':['result.kind.'+cap['output_contract']['kind']] if isinstance(cap.get('output_contract',{}).get('kind'),str) else [],
                      'required_parameters':cap.get('input_contract',{}),
                      'required_dependencies':cap.get('dependencies',[]),
                      'limitations':cap.get('limitations',[]), 'requires':[],
                      'evidence_status':'live_manifest_declaration_not_executed'})
    for p in ExecutableOrganLibrary(root).list():
        source_digest(p['source_path'])
        nodes.append({'id':p['ref'],'module':'organ','description':p['purpose'],'source':p['source_path'],
                      'accepts':['interface.'+t for t in p['requires']],
                      'requires':['interface.'+t for t in p['requires']],
                      'provides':['interface.'+t for t in p['provides']],
                      'project_types':p['project_types'],'required_parameters':p['parameters'],
                      'limitations':p['limitations'],'evidence_status':'installed_package_not_executed'})
    for name,source,fn,description in REQUEST_BUILDERS:
        if not source_digest(source):
            excluded.append({'id':name,'reason':'source unavailable'});continue
        tree=ast.parse((root/source).read_text())
        if not any(isinstance(n,ast.FunctionDef) and n.name==fn for n in tree.body):
            excluded.append({'id':name,'reason':'declared function unavailable'});continue
        nodes.append({'id':name,'module':'request-builder','description':description,
                      'source':{'path':source,'function':fn,'sha256':sources[source]},
                      'accepts':[], 'requires':[], 'provides':['request.kind.mixed-media-project'],
                      'required_parameters':'Caller supplies path and function-specific arguments; see MEDIA_WORKBENCH.md, DONOR_ABSORPTION.md WORKSHOP_PIPELINE.md and RTS_REFERENCE_FOUNDRY.md.',
                      'evidence_status':'explicit_source_adapter_not_executed'})
    # The manifest content, including implementation declarations, participates in identity.
    digest=hashlib.sha256(json.dumps({'nodes':nodes,'sources':sources,'excluded':excluded},sort_keys=True).encode()).hexdigest()
    return nodes, {'catalog_sha256':digest,'source_sha256':sources,'excluded_adapters':excluded,
                   'coverage':'Live capability manifests, installed executable organs, explicit request builders. Descriptive anatomy and other APIs are not implicitly executable.'}


def connect_nodes(nodes):
    _bounded(len(nodes),'catalog size',0,256)
    identities=[(n['module'],n['id']) for n in nodes]
    if len(set(identities))!=len(identities):raise ValueError('duplicate catalog identity')
    modules={};edges=[]
    for n in nodes:modules.setdefault(n['module'],[]).append(n)
    for a in nodes:
        for b in nodes:
            if a is b:continue
            if a.get('project_types') and b.get('project_types') and not set(a['project_types'])&set(b['project_types']):continue
            for token in sorted(set(a['provides'])&set(b['accepts'])):
                edges.append({'from':a['module'],'to':b['module'],'producer_capability':a['id'],
                              'consumer_capability':b['id'],'provided':token,'accepted':token,
                              'match':'exact_case_sensitive','score':3,'status':'declared_contract_not_tested'})
                if len(edges)>4096:raise ValueError('catalog exceeds 4096 candidate edges')
    graph=build_pipeline_graph({'modules':[{'module':k,'capabilities':v} for k,v in modules.items()], 'graph':{'edges':edges}})
    lookup={n['module']+'::'+n['id']:n for n in nodes}
    for n in graph['nodes']:
        for key in ('requires','required_parameters','required_dependencies','limitations','project_types'):
            n[key]=lookup[n['id']].get(key,[])
    return graph


def map_capabilities(root, goal=None, max_hops=4, limit=30, search_budget=10000):
    nodes,identity=installed_nodes(root)
    return map_nodes(nodes,goal,max_hops,limit,search_budget,identity)


def map_nodes(nodes, goal=None, max_hops=4, limit=30, search_budget=10000, identity=None):
    _bounded(max_hops,'max_hops',1,6);_bounded(limit,'limit',1,200);_bounded(search_budget,'search_budget',1,50000)
    if goal is not None and (not isinstance(goal,str) or not goal.strip() or len(goal)>200):raise ValueError('goal must contain 1..200 characters')
    goal=goal.strip() if goal else None
    graph=connect_nodes(nodes);lookup={n['id']:n for n in graph['nodes']}
    adjacency={n:[] for n in lookup}
    for e in graph['edges']:adjacency[e['from']].append(e)
    def matches(n):return goal is None or any(t==goal or t.startswith(goal+'.') for t in n['provides'])
    # Goal pruning before traversal avoids losing a relevant path behind a global top-N slice.
    relevant={n['id'] for n in graph['nodes'] if matches(n)}
    if goal:
        for _ in range(max_hops):
            relevant |= {e['from'] for e in graph['edges'] if e['to'] in relevant}
    queue=deque(([n],[]) for n in sorted(relevant));results=[];seen=set();explored=0;queue_cut=False
    while queue and explored<search_budget and len(results)<limit:
        path,edges=queue.popleft();explored+=1;last=lookup[path[-1]]
        if edges and matches(last) and tuple(path) not in seen:
            seen.add(tuple(path));available=set();needed=[]
            for n in path:
                missing=sorted(set(lookup[n]['requires'])-available)
                if missing:needed.append({'node':n,'interfaces':missing})
                available.update(lookup[n]['provides'])
            results.append({'id':pipeline_id(path),'nodes':path,'terminal_outputs':last['provides'],
                            'status':path_status(edges),'edges':edges,'additional_required_interfaces':needed,
                            'required_parameters':{n:lookup[n]['required_parameters'] for n in path},
                            'required_dependencies':{n:lookup[n]['required_dependencies'] for n in path if lookup[n]['required_dependencies']},
                            'truth_boundary':BOUNDARY})
        if len(edges)>=max_hops:continue
        for edge in adjacency[path[-1]]:
            nxt=edge['to']
            if nxt in path or nxt not in relevant:continue
            types=[set(lookup[n]['project_types']) for n in path+[nxt] if lookup[n]['project_types']]
            if types and not set.intersection(*types):continue
            queue.append((path+[nxt],edges+[edge]))
        # Queue allocation is bounded independently of visited-state work.
        if len(queue)>search_budget:
            queue=deque(list(queue)[:search_budget]);queue_cut=True
    truncated=bool(queue) or queue_cut
    incoming={(e['to'],e['accepted']) for e in graph['edges']}
    gaps=[{'node':n['id'],'interface':t} for n in graph['nodes'] for t in n['requires'] if (n['id'],t) not in incoming]
    return {'schema':'axm.uc.pipeline-map/v0.1','identity':identity or {},'goal':goal,'graph':graph,
            'single_capabilities':[n['id'] for n in graph['nodes'] if goal and matches(n)],
            'pipelines':results,'missing_interface_providers':gaps,
            'search':{'states_visited':explored,'budget':search_budget,'max_hops':max_hops,'limit':limit,
                      'truncated':truncated,'complete_within_hop_limit':not truncated,'order':'deterministic breadth-first; not a quality ranking'},
            'truth_boundary':BOUNDARY}
