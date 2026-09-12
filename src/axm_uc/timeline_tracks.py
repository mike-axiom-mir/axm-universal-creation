"""Validated local adapter around the pinned FrameState integer track sampler."""
from .donor_timeline import sample


def sample_track(track, frame, start=0, end=60):
    for value in (frame,start,end):
        if type(value) is not int: raise ValueError('Frame positions must be integers')
    if end <= start: raise ValueError('End must follow start')
    def integer(value):
        if type(value) is not int or abs(value)>10**12: raise ValueError('Track values must be bounded integers')
    def easing(value):
        if value not in ('linear','smoothstep','hold'): raise ValueError('Unknown easing')
    if type(track) is int: integer(track)
    elif isinstance(track,dict):
        if 'keyframes' in track:
            if set(track)!={'keyframes'}:raise ValueError('Unexpected track fields')
            rows=track['keyframes']
            if not isinstance(rows,list) or not 1<=len(rows)<=256:raise ValueError('Expected 1..256 keyframes')
            previous=None
            for row in rows:
                if not isinstance(row,dict) or not {'frame','value'}<=set(row) or set(row)-{'frame','value','easing'}:raise ValueError('Invalid keyframe')
                integer(row['frame']);integer(row['value']);easing(row.get('easing','linear'))
                if previous is not None and row['frame']<=previous:raise ValueError('Keyframes must increase strictly')
                previous=row['frame']
        else:
            if not track or set(track)-{'from','to','value','easing'}:raise ValueError('Invalid scalar track')
            if not set(track)&{'from','value'}:raise ValueError('Track needs from or value')
            for key in set(track)-{'easing'}:integer(track[key])
            easing(track.get('easing','linear'))
    else: raise ValueError('Expected integer or track object')
    return sample(track,frame,start,end)
