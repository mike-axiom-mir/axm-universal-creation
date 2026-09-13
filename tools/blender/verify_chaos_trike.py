"""Independent exported geometry and clip inspection; no authoring pose calls."""
import argparse,json
from pathlib import Path
from verify_globe_companion import inspect
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
m=json.loads((a.directory/'vehicle-manifest.json').read_text())
rows=[inspect(a.directory/v['path'],m) for v in m['exports'].values()]
r={'pass':all(v['pass'] for v in rows),'artifacts':rows,'limits':'Fresh-import structural and motion checks; no target engine or driving physics validation.'}
(a.directory/'verification.json').write_text(json.dumps(r,indent=2)+'\n')
print('TRIKE_VERIFIED',r['pass'])
if not r['pass']:raise SystemExit(1)
