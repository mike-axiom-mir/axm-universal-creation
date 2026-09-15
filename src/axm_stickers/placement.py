"""Renderer-independent 2D affine and rigid 3D socket attachment conventions."""
import math


def vector(value,n):
    if not isinstance(value,list) or len(value) != n or any(
            type(x) not in (int,float) or not math.isfinite(x) or abs(x) > 1e6 for x in value):
        raise ValueError(f'expected {n} bounded finite numbers')
    return list(value)


def identity(): return [1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]


def multiply(a,b):
    return [sum(a[r*4+k]*b[k*4+c] for k in range(4)) for r in range(4) for c in range(4)]


def rigid(value):
    m = vector(value,16)
    if m[12:] != [0,0,0,1]: raise ValueError('expected affine row-major matrix')
    for i in range(3):
        for j in range(3):
            if abs(sum(m[k*4+i]*m[k*4+j] for k in range(3)) - (i==j)) > 1e-6:
                raise ValueError('socket frame must be rigid; scale is an instance control')
    det = m[0]*(m[5]*m[10]-m[6]*m[9])-m[1]*(m[4]*m[10]-m[6]*m[8])+m[2]*(m[4]*m[9]-m[5]*m[8])
    if abs(det-1) > 1e-6: raise ValueError('reflected socket frames are unsupported')
    return m


def inverse_rigid(value):
    m = rigid(value)
    result = identity()
    for r in range(3):
        for c in range(3): result[r*4+c] = m[c*4+r]
        result[r*4+3] = -sum(result[r*4+c]*m[c*4+3] for c in range(3))
    return result


def compatible(definition,target,space):
    if not isinstance(target,dict) or target.get('space') != space or definition['attachment']['space'] != space:
        raise ValueError('incompatible attachment space')
    if target.get('socket') != definition['attachment']['socket']:
        raise ValueError('incompatible socket kind')


def placement_2d(definition,placed,target):
    """Six values: x'=a*x+c*y+tx; y'=b*x+d*y+ty, pixel-edge coordinates."""
    compatible(definition,target,'2d')
    if set(target) != {'space','socket'}: raise ValueError('unsupported 2D target fields')
    p = placed['placement']
    if set(p)-{'translation','scale','rotation','opacity'}: raise ValueError('unsupported 2D placement controls')
    x,y = vector(p.get('translation',[0,0]),2)
    sx,sy = vector(p.get('scale',[1,1]),2)
    angle = vector([p.get('rotation',0)],1)[0]
    opacity = vector([p.get('opacity',1)],1)[0]
    if not .001 <= sx <= 100 or not .001 <= sy <= 100 or not 0 <= opacity <= 1:
        raise ValueError('scale/opacity outside bounds')
    c,s = math.cos(math.radians(angle)),math.sin(math.radians(angle))
    a,b,d,e = c*sx,s*sx,-s*sy,c*sy
    ax,ay = vector(definition['attachment']['anchor'],2)
    return [a,b,d,e,x-a*ax-d*ay,y-b*ax-e*ay]


def attachment_matrix(definition,placed,target):
    """World = target socket * local offset * inverse(sticker mount frame)."""
    compatible(definition,target,'3d')
    if set(target) != {'space','socket','frame'}: raise ValueError('unsupported 3D target fields')
    p = placed['placement']
    if set(p)-{'offset','scale'}: raise ValueError('unsupported 3D placement controls')
    offset = rigid(p.get('offset',identity()))
    scale = vector([p.get('scale',1)],1)[0]
    if not .001 <= scale <= 100: raise ValueError('scale outside bounds')
    for r in range(3):
        for c in range(3): offset[r*4+c] *= scale
    return multiply(multiply(rigid(target['frame']),offset),inverse_rigid(definition['attachment']['anchor']))
