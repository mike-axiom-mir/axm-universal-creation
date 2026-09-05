"""Exercise the generic machine reviewer on an existing terminal pack, read-only.

python tools/review_terminal_contracts.py --pack EXISTING_PACK --output NEW_DIRECTORY
Negative controls change only an in-memory contract, never the sealed GLBs.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_uc.asset_geometry import CONTRACT_SCHEMA,review_static_glb

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pack',required=True);parser.add_argument('--output',required=True);parser.add_argument('--collision-contract',help='Reuse an explicitly selected placement contract for a new source revision');args=parser.parse_args()
    pack=Path(args.pack).resolve();out=Path(args.output).resolve()
    if out==pack or pack in out.parents:raise ValueError('Evidence output must be outside the existing pack')
    out.mkdir(parents=True,exist_ok=False)
    data=json.loads((pack/'assets/manifest.json').read_text());collision=json.loads((Path(args.collision_contract) if args.collision_contract else pack/'collision-contract.json').read_text());rows=[]
    if len(data['assets'])!=6 or len({a['asset'] for a in data['assets']})!=6:raise ValueError('Expected six distinct terminal assets')
    for asset in data['assets']:
        name=asset['asset'];path=pack/'assets'/name/(name+'.glb');before=hashlib.sha256(path.read_bytes()).hexdigest()
        if before!=asset['sha256']:raise ValueError('Input asset hash differs from its manifest')
        boxes=next(row['boxes'] for row in collision['assets'] if row['asset']==name)
        converted=[{'name':b['name'],'min':[b['x']-b['w']/2,b['bottom'],b['z']-b['d']/2],'max':[b['x']+b['w']/2,b['h'],b['z']+b['d']/2]} for b in boxes]
        width,depth=asset['spec']['footprint']
        spec={'schema':CONTRACT_SCHEMA,'bounds':{'min':[-width/2,0,-depth/2],'max':[width/2,asset['spec']['cap'],depth/2]},'floor_y':0,'tolerance_m':.00002,'require_root_identity':True,'max_triangles':5000,'max_primitives':12,'markers':asset['markers'],'collision_boxes':converted}
        good=review_static_glb(path,spec);negative=[]
        controls={'short-envelope':'OUTSIDE_ENVELOPE','missing-upper-collision':'COLLISION_COVERAGE_UNPROVEN','wrong-marker':'MARKER_POSITION','low-triangle-budget':'BUDGET_EXCEEDED'}
        for kind,expected_code in controls.items():
            bad=copy.deepcopy(spec)
            if kind=='short-envelope':bad['bounds']['max'][1]=asset['imported']['bounds_xyz_m'][1][1]-.05
            if kind=='missing-upper-collision':bad['collision_boxes']=converted[:1]
            if kind=='wrong-marker':bad['markers']['Contact']=[0,.05,0]
            if kind=='low-triangle-budget':bad['max_triangles']=asset['imported']['triangles']-1
            review=review_static_glb(path,bad);negative.append({'case':kind,'status':review['status'],'expected_code':expected_code,'detected':review['status']=='FAIL' and expected_code in review['finding_counts'],'finding_count':review['finding_count'],'finding_counts':review['finding_counts'],'findings':review['findings']})
        unchanged=hashlib.sha256(path.read_bytes()).hexdigest()==before
        row={'asset':name,'positive':good,'negative_controls':negative,'input_unchanged':unchanged};rows.append(row)
        (out/(name+'.json')).write_text(json.dumps(row,indent=2),encoding='utf-8')
    passed=all(r['positive']['status']=='PASS' and r['input_unchanged'] and all(n['detected'] for n in r['negative_controls']) for r in rows)
    summary={'status':'PASS' if passed else 'FAIL','assets':len(rows),'positive_passes':sum(r['positive']['status']=='PASS' for r in rows),'negative_controls':sum(len(r['negative_controls']) for r in rows),'negative_failures_detected':sum(n['detected'] for r in rows for n in r['negative_controls']),'triangles':sum(r['positive']['measurements'].get('triangles',0) for r in rows),'all_inputs_unchanged':all(r['input_unchanged'] for r in rows),'asset_results':[{'asset':r['asset'],'sha256':r['positive']['artifact_sha256'],'contract_sha256':r['positive']['contract_sha256'],'status':r['positive']['status'],'measurements':r['positive']['measurements'],'finding_counts':r['positive']['finding_counts']} for r in rows],'scope':'Actual exported static asset bytes and in-memory contract mutations; no rendering, controller, runtime collision or visual acceptance claim.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
