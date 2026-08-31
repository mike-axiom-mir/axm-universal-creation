from __future__ import annotations

import math
from typing import Any

from .visual_base import _hash2, png_bytes

SPRITES = (
    "bot", "worker", "soldier", "vehicle", "tank", "drone", "turret", "tree", "rock",
    "crystal", "crate", "barrel", "pickup", "building", "spaceship", "creature",
    "orb", "effect-burst", "projectile", "shield", "coin", "heart", "star", "portal",
)


def _canvas(w: int, h: int) -> list[list[tuple[int,int,int,int]]]:
    return [[(0,0,0,0) for _ in range(w)] for _ in range(h)]


def _put(img, x, y, c):
    if 0 <= y < len(img) and 0 <= x < len(img[0]): img[y][x] = c


def _rect(img, x0, y0, x1, y1, c):
    for y in range(max(0,y0), min(len(img),y1)):
        for x in range(max(0,x0), min(len(img[0]),x1)): img[y][x]=c


def _circle(img, cx, cy, r, c):
    rr=r*r
    for y in range(cy-r, cy+r+1):
        for x in range(cx-r, cx+r+1):
            if (x-cx)**2+(y-cy)**2 <= rr: _put(img,x,y,c)


def _line(img, x0,y0,x1,y1,c,th=1):
    dx,dy=x1-x0,y1-y0; steps=max(abs(dx),abs(dy),1)
    for i in range(steps+1):
        x=round(x0+dx*i/steps); y=round(y0+dy*i/steps)
        _rect(img,x-th,y-th,x+th+1,y+th+1,c)


def _frame(kind: str, size: int, seed: int, frame: int) -> list[list[tuple[int,int,int,int]]]:
    img=_canvas(size,size); cx=size//2; cy=size//2
    hue=int(_hash2(seed+17, frame, len(kind))*110)
    base=(50+hue, 95+(hue//2), 145+(hue//3),255)
    hi=(min(255,base[0]+80),min(255,base[1]+80),min(255,base[2]+80),255)
    dark=(max(0,base[0]-35),max(0,base[1]-35),max(0,base[2]-35),255)
    pulse=frame%4
    if kind in {"bot","worker","soldier","creature"}:
        _circle(img,cx,cy-size//5,size//7,hi); _rect(img,cx-size//7,cy-size//12,cx+size//7,cy+size//5,base)
        swing=(-1 if frame%2 else 1)*size//10
        _line(img,cx-size//8,cy,cx-size//4-swing,cy+size//5,dark,1); _line(img,cx+size//8,cy,cx+size//4+swing,cy+size//5,dark,1)
        _line(img,cx-size//12,cy+size//5,cx-size//8+swing,cy+size//3,dark,1); _line(img,cx+size//12,cy+size//5,cx+size//8-swing,cy+size//3,dark,1)
        if kind=="soldier": _rect(img,cx+size//7,cy-size//12,cx+size//3,cy,hi)
        if kind=="bot": _rect(img,cx-size//12,cy-size//4,cx+size//12,cy-size//5,dark)
    elif kind in {"vehicle","tank","turret"}:
        _rect(img,size//5,cy-size//8,size*4//5,cy+size//7,base); _rect(img,size//3,cy-size//4,size*2//3,cy-size//8,hi)
        _circle(img,size//3,cy+size//6,size//10,dark); _circle(img,size*2//3,cy+size//6,size//10,dark)
        if kind in {"tank","turret"}: _line(img,cx,cy-size//5,size*5//6,cy-size//4,hi,2)
    elif kind=="drone":
        _circle(img,cx,cy,size//8,base)
        for sx,sy in ((-1,-1),(1,-1),(-1,1),(1,1)):
            _line(img,cx,cy,cx+sx*size//4,cy+sy*size//4,dark,1); _circle(img,cx+sx*size//4,cy+sy*size//4,size//12,hi)
    elif kind=="tree":
        _rect(img,cx-size//12,cy,cx+size//12,size*5//6,dark); _circle(img,cx,cy-size//6,size//4,base); _circle(img,cx-size//7,cy-size//12,size//6,hi)
    elif kind in {"rock","crystal"}:
        for y in range(size):
            for x in range(size):
                d=math.hypot(x-cx,y-cy)
                if d < size*(.27 if kind=="rock" else .22) * (1+.15*math.sin(math.atan2(y-cy,x-cx)*5)):
                    _put(img,x,y,hi if (x+y)%7<3 else base)
        if kind=="crystal": _line(img,cx,cy,cx,size//6,hi,2)
    elif kind in {"crate","barrel","pickup","building"}:
        if kind=="barrel":
            _rect(img,cx-size//6,size//4,cx+size//6,size*3//4,base); _circle(img,cx,size//4,size//6,hi); _circle(img,cx,size*3//4,size//6,dark)
        else:
            pad=size//4; _rect(img,pad,pad,size-pad,size-pad,base); _line(img,pad,pad,size-pad,size-pad,hi,1); _line(img,size-pad,pad,pad,size-pad,dark,1)
            if kind=="building": _rect(img,size//3,size//2,size*2//3,size*3//4,dark)
    elif kind=="spaceship":
        for y in range(size//4,size*3//4):
            half=max(1,int((1-abs(y-cy)/(size/4))*size/3)); _rect(img,cx-half,y,cx+half,y+1,base)
        _line(img,cx,size//5,cx,size*4//5,hi,1)
    else:
        radius=size//5 + pulse
        _circle(img,cx,cy,radius,base); _circle(img,cx,cy,max(2,radius//2),hi)
        if kind in {"effect-burst","star","portal"}:
            for a in range(0,360,45):
                r=size//3; _line(img,cx,cy,cx+int(math.cos(math.radians(a))*r),cy+int(math.sin(math.radians(a))*r),hi,1)
    return img


def sprite_sheet_bytes(kind: str, *, seed: int=0, frame_size: int=32, frames: int=4, columns: int|None=None) -> tuple[bytes, dict[str, Any]]:
    kind=kind.strip().casefold()
    if kind not in SPRITES: raise KeyError(f"unknown sprite kind: {kind}")
    frame_size=max(8,min(256,int(frame_size))); frames=max(1,min(64,int(frames))); columns=max(1,min(frames,int(columns or frames)))
    rows=(frames+columns-1)//columns; width=columns*frame_size; height=rows*frame_size
    sheet=_canvas(width,height)
    for i in range(frames):
        fr=_frame(kind,frame_size,seed,i); ox=(i%columns)*frame_size; oy=(i//columns)*frame_size
        for y,row in enumerate(fr):
            sheet[oy+y][ox:ox+frame_size]=row
    return png_bytes(width,height,sheet,"RGBA"), {"kind":kind,"frame_size":frame_size,"frames":frames,"columns":columns,"rows":rows,"width":width,"height":height}
