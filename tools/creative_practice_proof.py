"""Reproducible offline practice cartridge; no model, browser or network."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from axm_uc.creative_practice import Practice
from axm_uc.fabric_noise import png_bytes
from axm_uc.studio_compositor import SCHEMA


def build(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    width, height = 128, 96
    paint, badge = bytearray(), bytearray()
    for y in range(height):
        for x in range(width):
            seam = x % 32 < 2 or y % 24 < 2
            nick = (x*31+y*17) % 107 < 3
            color = (37,46,60) if seam else ((127,146,155) if nick else (190+x//3,104+y//2,31))
            paint.extend((*color,255))
            # Original protected cyan chevron badge, above the experimental paint.
            on = 43 <= x < 85 and 28 <= y < 65 and abs(x-64) < (y-25)/2
            badge.extend((38,229,242,255) if on else (0,0,0,0))
    sources = {'paint':png_bytes(width,height,4,bytes(paint)),
               'badge':png_bytes(width,height,4,bytes(badge))}
    for key, body in sources.items(): (root / f'{key}.png').write_bytes(body)
    project = {'schema':SCHEMA, 'sources':{k:f'{k}.png' for k in sources},
               'recipe':{'schema':'axm.raster-composition/v1','canvas':{'width':width,'height':height},
                         'layers':[{'id':'paint','source_artifact_id':'paint'},
                                   {'id':'identity','source_artifact_id':'badge'}]}}
    database = root / 'practice.sqlite'
    with Practice(database) as p:
        p.profile('salvage', identity='AXM-practice-maker', direction='graphic', seed=471,
                  intent='Explore graphic paint treatments while retaining the source badge')
        first = p.start('salvage', project, root, checkpoint_every=2)['id']
        bad = p.tick(first, {'label':'missing-effect-probe','operations':[
            {'op':'change','id':'paint','patch':{'filters':[{'type':'missing-depth-emboss'}]}}]})
        assert bad['outcome'] == 'blocked'
        study = p.tick(first)
        assert study['outcome'] == 'rendered' and study['changed']
        assert bad['id'] in study['consumed_lessons']
        p.review(study['id'],'keep',actor='deterministic:proof',
                 reason='Select this changed rendering for replay; no artistic quality judgment')
        p.export(first, root / 'editable-study')
        p.control(first,'close')
        p.profile('surface',identity='AXM-practice-maker',direction='surface',parent='salvage')
        second = p.start('salvage',project,root)['id']
        p.control(second,'pause')
        before = p.journal(second)
        for _ in range(1000): p.tick(second)
        assert p.journal(second) == before
    # Delete the source files; resume must use exact captured source bytes.
    for key in sources: (root / f'{key}.png').unlink()
    with Practice(database) as p:
        p.control(second,'resume')
        next_study = p.tick(second)
        assert next_study['signature'] != study['signature']
        assert study['id'] in next_study['consumed_lessons']
        p.export(second,root / 'resumed-study',trial=next_study['id'])
        p.control(second,'close')
        for key,digest in p.status(second)['sources'].items():
            assert p.artifact(digest) == sources[key]
        p.backup(root / 'portable-copy.sqlite')
        receipt = {'schema':'axm.creative-practice-proof/v1',
                   'sessions':[first,second], 'failed_trial':bad['id'],
                   'first_choice':study['proposal']['label'],
                   'memory_informed_choice':next_study['proposal']['label'],
                   'consumed_lessons':next_study['consumed_lessons'],
                   'idle_ticks':1000, 'idle_events_added':0,
                   'source_bytes_preserved':True, 'replay_exact':True,
                   'profile_fork':'surface', 'database_bytes':database.stat().st_size,
                   'truth':'Actual Studio rendering, resume and evidence retrieval; no aesthetic acceptance or model-weight training.'}
    with Practice(root / 'portable-copy.sqlite') as portable:
        assert portable.status(second)['status'] == 'closed'
        assert portable.trial(study['id'])['png'] == study['png']
    (root / 'proof.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    (root / 'README.txt').write_text('Open practice.sqlite with the axm-practice API/CLI.\n'
        'editable-study and resumed-study are replayable Studio projects.\n'
        'The portable copy contains profiles, captured sources, outputs and session evidence.\n'
        'No remote services are needed. Python 3.11+ and local Node.js are required for rendering.\n',encoding='utf-8')
    return receipt


if __name__ == '__main__':
    print(json.dumps(build(sys.argv[1]),indent=2))
