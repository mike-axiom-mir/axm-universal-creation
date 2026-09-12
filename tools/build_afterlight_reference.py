"""Build an authored lighting reference through UC's existing static-web path.

The machine validates and preserves supplied HTML/CSS/JS. It does not invent this
artwork, select its subject, or gain a live reactive-light organ from this example.
"""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_uc.machine import UniversalCreationMachine


def build(destination):
    destination=destination.resolve()
    destination.relative_to((ROOT/'creations').resolve())
    if destination.exists():
        raise ValueError('Choose a new output directory under creations')
    source=ROOT/'examples/browser/lantern'
    files={name:(source/name).read_text() for name in ('index.html','style.css','app.js')}
    machine=UniversalCreationMachine(ROOT)
    result=machine.create({'kind':'static-web-project','direction':'Preserve and validate the supplied Afterlight visual reference.', 'inputs':{'path':str(destination),'project_type':'static-web','files':files}})
    if result.get('type')!='CREATION_RESULT' or not result['result']['validation']['passed']:
        raise RuntimeError(json.dumps(result))
    verification=machine.create({'kind':'verify-project','inputs':{'path':str(destination),'project_type':'static-web','expected_files':files}})
    if not verification.get('result',{}).get('passed'):
        raise RuntimeError(json.dumps(verification))
    receipt={'authorship':'assistant-authored visual reference; machine-preserved supplied source','new_source_invented_by_machine':False,'live_reactive_light_organ_installed':False,'verification':verification['result']}
    (destination/'reference-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'created':str(destination),'passed':True,'machine_invented_source':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    build(parser.parse_args().destination)
