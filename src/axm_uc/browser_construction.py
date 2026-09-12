"""Optional bounded placement/economy contract for browser arenas."""
from .browser_construction_source import CONSTRUCTION_JS, CONSTRUCTION_UI_JS


def validate_construction(raw, viewport, tower, player):
    # Reuse the arena's strict scalar validators without a module-level cycle.
    from .browser_game import _object, _integer, _text, BrowserGameError
    c=_object({k:v for k,v in raw.items() if k not in {'cols','rows'}} if isinstance(raw,dict) else raw,'construction',{'cell_size','initial_credits','blocked','catalog'})
    size=_integer(c['cell_size'],'cell_size',40,160)
    cols=viewport['width']//size; rows=viewport['height']//size
    if ('cols' in raw and raw['cols']!=cols) or ('rows' in raw and raw['rows']!=rows):raise BrowserGameError('Derived grid dimensions do not match viewport')
    credits=_integer(c['initial_credits'],'initial_credits',0,1_000_000)
    if not isinstance(c['blocked'],list) or len(c['blocked'])>cols*rows:
        raise BrowserGameError('blocked must be a bounded cell list')
    blocked=set()
    for cell in c['blocked']:
        if not isinstance(cell,list) or len(cell)!=2:raise BrowserGameError('blocked cells must be [column,row]')
        blocked.add((_integer(cell[0],'column',0,cols-1),_integer(cell[1],'row',0,rows-1)))
    # Core footprint and initial player position are reserved automatically.
    for col in range(cols):
        for row in range(rows):
            x=col*size;y=row*size
            if x<tower['x']+tower['width'] and x+size>tower['x'] and y<tower['y']+tower['height'] and y+size>tower['y']:
                blocked.add((col,row))
    blocked.add((min(cols-1,int(player['x']//size)),min(rows-1,int(player['y']//size))))
    cat=_object(c['catalog'],'catalog',{'generator','turret','repair'})
    result={}
    for kind,entry in cat.items():
        e=_object(entry,kind,{'label','cost','rate','range'})
        result[kind]={'label':_text(e['label'],'label',40),'cost':_integer(e['cost'],'cost',1,1000000),'rate':_integer(e['rate'],'rate',1,1000),'range':_integer(e['range'],'range',0,2000)}
    return {'cell_size':size,'cols':cols,'rows':rows,'initial_credits':credits,'blocked':[list(v) for v in sorted(blocked)],'catalog':result}
