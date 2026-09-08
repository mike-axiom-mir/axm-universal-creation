"""Dependency-free cross sections shared by authored mesh builders."""
import math


def octagon(w, d, c):
    """Convex chamfered rectangle even for very thin service panels."""
    if not all(math.isfinite(v) for v in (w,d,c)) or w<=0 or d<=0 or c<=0:
        raise ValueError('finite positive panel dimensions and chamfer required')
    c=min(c,w*.49,d*.49)
    x,y=w/2,d/2
    return [(-x+c,-y),(x-c,-y),(x,-y+c),(x,y-c),
            (x-c,y),(-x+c,y),(-x,y-c),(-x,-y+c)]
