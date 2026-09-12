"""Offline dimensional presets and editable layout scaffolds, not finished artwork."""
from copy import deepcopy
from html import escape
from math import ceil, isfinite

FORMATS = {
    'poker-card': ('mm', 63.5, 88.9),
    'a4': ('mm', 210, 297), 'a5': ('mm', 148, 210), 'a6': ('mm', 105, 148),
    'us-letter': ('mm', 215.9, 279.4),
    'hd': ('px', 1280, 720), 'full-hd': ('px', 1920, 1080),
    'qhd': ('px', 2560, 1440), 'uhd': ('px', 3840, 2160),
    'portrait-hd': ('px', 1080, 1920), 'square': ('px', 1024, 1024),
    'icon': ('px', 256, 256),
}
# Normalized semantic rectangles within the safe area: x, y, width, height.
LAYOUTS = {
    'collectible-card': {'title': (.0,.0,1,.09), 'artwork': (0,.12,1,.48),
                         'abilities': (0,.63,1,.23), 'stats': (0,.89,1,.11)},
    'card-back': {'identity': (0,0,1,.15), 'emblem': (.15,.23,.7,.54), 'edition': (0,.87,1,.13)},
    'game-hud': {'status': (0,0,.32,.12), 'objective': (.37,0,.4,.12),
                 'minimap': (.81,0,.19,.25), 'playfield': (0,.29,1,.49),
                 'abilities': (.27,.83,.46,.17), 'resources': (0,.83,.23,.17)},
    'inventory': {'title': (0,0,1,.1), 'items': (0,.14,.62,.86), 'details': (.66,.14,.34,.86)},
    'main-menu': {'title': (.1,.08,.8,.18), 'actions': (.3,.35,.4,.5), 'footer': (0,.92,1,.08)},
    'poster': {'headline': (0,0,1,.16), 'artwork': (0,.2,1,.55), 'details': (0,.79,1,.21)},
}


def catalog():
    return {'formats': {k: {'unit': v[0], 'width': v[1], 'height': v[2]} for k,v in FORMATS.items()},
            'layouts': deepcopy(LAYOUTS), 'screen_note': 'Pixel sizes are design canvases, not device or responsive-layout guarantees.'}


def resolve_format(name, dpi=300, bleed=0, safe=0, landscape=False):
    if name not in FORMATS:
        raise ValueError('Unknown format: '+str(name))
    for key, value in [('dpi',dpi),('bleed',bleed),('safe',safe)]:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value):
            raise ValueError(key+' must be a finite number')
    if not 36 <= dpi <= 1200 or bleed < 0 or safe < 0:
        raise ValueError('DPI must be 36..1200; bleed and safe inset must be nonnegative')
    if not isinstance(landscape,bool):
        raise ValueError('landscape must be boolean')
    unit,w,h=FORMATS[name]
    if landscape: w,h=max(w,h),min(w,h)
    if safe*2 >= min(w,h) or bleed > min(w,h)/2:
        raise ValueError('Insets exceed the format bounds')
    if unit=='px' and bleed:
        raise ValueError('Print bleed is unavailable for pixel canvases')
    scale=dpi/25.4 if unit=='mm' else 1
    return {'id':name,'unit':unit,'dpi':dpi if unit=='mm' else None,
            'canvas':[w+2*bleed,h+2*bleed], 'trim':[bleed,bleed,w,h],
            'safe':[bleed+safe,bleed+safe,w-2*safe,h-2*safe],
            'raster_pixels':[ceil((w+2*bleed)*scale),ceil((h+2*bleed)*scale)]}


def layout_project(format_name, layout, title='Untitled creation', **options):
    if layout not in LAYOUTS: raise ValueError('Unknown layout: '+str(layout))
    if not isinstance(title,str) or not 1 <= len(title) <= 160:
        raise ValueError('Title must contain 1..160 characters')
    f=resolve_format(format_name,**options);w,h=f['canvas'];sx,sy,sw,sh=f['safe']
    regions={k:[sx+x*sw,sy+y*sh,rw*sw,rh*sh] for k,(x,y,rw,rh) in LAYOUTS[layout].items()}
    def rect(box,stroke,fill='none',dash=''):
        x,y,rw,rh=box
        return f'<rect x="{x:g}" y="{y:g}" width="{rw:g}" height="{rh:g}" fill="{fill}" stroke="{stroke}" stroke-width="{min(w,h)/500:g}" {dash}/>'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}{f["unit"]}" height="{h:g}{f["unit"]}" viewBox="0 0 {w:g} {h:g}"><title>{escape(title)}</title>'
    svg+=rect([0,0,w,h],'#172c3b','#101d29')
    for label,box in regions.items():
        svg+=f'<g id="{label}">'+rect(box,'#78bdbb','#203745')
        svg+=f'<text x="{box[0]+sw*.025:g}" y="{box[1]+min(box[3]*.55,sh*.035):g}" fill="#deeeee" font-family="sans-serif" font-size="{min(sw*.04,sh*.025):g}">{escape(label.upper())}</text></g>'
    svg+=rect(f['trim'],'#f7c66c',dash='stroke-dasharray="2 1"')+rect(f['safe'],'#a7e3ba',dash='stroke-dasharray="1 1"')+'</svg>'
    import json
    manifest={'schema':'axm.format-layout/v0.1','title':title,'format':f,'layout':layout,'regions':regions,
              'truth':'Editable layout scaffold; no artwork, gameplay, CMYK conversion or printer certification.',
              'guides':'Gold: trim. Green: safe area. SVG includes guides; remove guide rectangles before final art export.'}
    html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+escape(title)+'</title><style>body{background:#0b141d;color:#e2eded;font:16px system-ui;margin:32px}img{display:block;max-width:100%;max-height:75vh;margin:24px 0}a{color:#9de0d9}</style><h1>'+escape(title)+'</h1><p>Editable layout scaffold · Gold: trim · Green: safe area</p><img src="layout.svg" alt="'+escape(layout,quote=True)+' layout"><a href="layout.svg" download>Download SVG</a> · <a href="layout.json" download>Download dimensions and regions</a></html>'
    return {'id':'axm.layout.'+layout,'version':'0.1.0','project_type':'static-web',
            'files':{'index.html':html,'layout.svg':svg,'layout.json':json.dumps(manifest,indent=2)}}
