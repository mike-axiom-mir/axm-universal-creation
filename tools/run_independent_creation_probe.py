"""Bounded autonomous-composition probe; this driver is an external orchestrator.

No model/network calls, generated source edits, candidate installation or adoption.
The machine selects the supported recipe and organ closure; the caller supplies
requirements, labels and color. Open-ended invention remains a separate probe.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from axm_uc.machine import UniversalCreationMachine


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def body_digest():
    h = hashlib.sha256()
    for directory in ('capabilities/live', 'executable-organs'):
        for path in sorted((ROOT / directory).glob('*.json')):
            h.update(str(path.relative_to(ROOT)).encode());h.update(path.read_bytes())
    return h.hexdigest()


def run(destination):
    destination = destination.resolve()
    destination.relative_to((ROOT / 'creations').resolve())
    if destination == (ROOT / 'creations').resolve():
        raise ValueError('Use a new child directory under creations')
    destination.mkdir(parents=True, exist_ok=False)
    machine = UniversalCreationMachine(ROOT)
    before = body_digest()
    open_request = {'kind':'invent-new-browser-experience', 'direction':'Independently invent and create a playful interactive browser experience. Choose its design yourself.', 'inputs':{'path':str(destination/'open-ended')}}
    open_result = machine.create(open_request)
    dump(destination/'open-ended-request.json',open_request)
    dump(destination/'open-ended-result.json',open_result)

    request = json.loads((ROOT/'examples/requests/probe_interface_lantern.json').read_text())
    request['inputs']['path'] = str(destination/'lantern')
    request['inputs']['report_path'] = str(destination/'verification.json')
    dump(destination/'bounded-request.json',request)
    exploration = machine.create({'kind':'explore-gap-candidate','inputs':{'operation':'materialize-and-test','path':str(destination/'candidate'),'request':request}})
    dump(destination/'exploration.json',exploration)
    result = exploration.get('result',{})
    if result.get('passed') is not True:
        raise RuntimeError('Detached trial did not pass; result preserved, no execution')
    # Explicit driver decision to run the tested detached recipe; not admission.
    manifest = json.loads((destination/'candidate/capability.json').read_text())
    execution = machine.capabilities.invoke(manifest, request['inputs'])
    dump(destination/'execution.json',execution)
    report = json.loads((destination/'verification.json').read_text())
    if report != execution['verification'] or not report.get('passed'):
        raise RuntimeError('Independent report did not match successful verification')

    missing = copy.deepcopy(request)
    missing['kind'] = 'unimplemented-reactive-lantern'
    missing['inputs']['organ_goal']['required_interfaces'] = ['reactive-light']
    missing['inputs']['path'] = str(destination/'missing-interface')
    missing_result = machine.create({'kind':'analyze-creation-gap','inputs':{'operation':'analyze','request':missing}})
    dump(destination/'missing-interface-result.json',missing_result)
    discovery = execution['production']['organ_discovery']
    after = body_digest()
    summary = {
        'schema':'axm.independent-creation-probe/v0.1',
        'open_ended_status':open_result.get('gap_synthesis',{}).get('status',open_result.get('type')),
        'bounded_trial_status':result['status'],
        'recipe_steps':[{'id':x['id'],'capability':x['capability']} for x in manifest['implementation']['steps']],
        'selected_organs':discovery['selected_candidate']['package_refs'],
        'verification_passed':report['passed'],
        'verification_report_matches':True,
        'generated_files':[{ 'path':p.name, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((destination/'lantern').iterdir()) if p.is_file()],
        'live_body_unchanged':before==after,
        'candidate_installed':machine.capabilities.route(request['kind']) is not None,
        'assistant_supplied':['goal interfaces','labels','color','this experiment driver','decision to execute the tested detached recipe'],
        'machine_derived':['organ package selection','dependency closure','build/verify/report recipe','candidate manifest','request-shaped test','emitted files from installed templates','verification report'],
        'new_source_invented':False,
        'browser_observed_by_this_driver':False,
        'missing_interface_status':missing_result.get('result',{}).get('status'),
    }
    if not summary['live_body_unchanged'] or summary['candidate_installed']:
        raise RuntimeError('Unexpected live-body change; preserve evidence for inspection')
    dump(destination/'summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path,help='New directory under this checkout\'s creations/')
    run(parser.parse_args().destination)
