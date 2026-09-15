"""Opt-in, local creative practice: evidence memory, never model-weight training.

One SQLite cartridge holds all profiles, session journals and deduplicated source
and result bytes. A tick attempts one bounded Studio edit; it creates no service.
Human, machine and AI callers use the same proposal/review API.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

from . import studio_compositor as studio

SCHEMA = 'axm.creative-practice/v1'
APP_ID = 0x41585052
MAX_JSON = 1024 * 1024
MAX_DB = 256 * 1024 * 1024
DIRECTIONS = ('free', 'graphic', 'surface')


def _json(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode('utf-8')) > MAX_JSON:
        raise ValueError('practice JSON exceeds 1 MiB')
    return encoded


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _text(value, label, maximum=240):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{label} requires 1..{maximum} characters')
    return value


def _integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label} must be an integer in {low}..{high}')
    return value


def _engine():
    # Invalidate automatic negative evidence when either implementation changes.
    return _sha(Path(__file__).read_bytes() + Path(studio.__file__).read_bytes()
                + (studio.DATA / 'raster-compositor.js').read_bytes()
                + (studio.DATA / 'compose-runner.cjs').read_bytes())


def candidates(project, direction='free', seed=0):
    """Small executable starter repertoire; explicit proposals can use all edits.

    No inferred quality score. Select the first visible layer and retain its
    existing filters; free practice explores both repertoires in seeded order.
    """
    if direction not in DIRECTIONS:
        raise ValueError('unknown practice direction')
    layers = project['recipe']['layers']
    layer = next((x for x in layers if x.get('visible', True)), None)
    if layer is None:
        return []
    effects = [('graphic', 'ink-threshold', {'type':'threshold', 'value':0.45}),
               ('graphic', 'poster-four', {'type':'posterize', 'levels':4}),
               ('graphic', 'pixel-blocks', {'type':'pixelate', 'size':4}),
               ('surface', 'soften', {'type':'blur', 'radius':1}),
               ('surface', 'edge-definition', {'type':'sharpen', 'amount':0.6}),
               ('surface', 'contrast-study', {'type':'contrast', 'value':0.25})]
    output = []
    for family, label, effect in effects:
        if direction == 'free' or direction == family:
            output.append({'label':label, 'operations':[{'op':'change', 'id':layer['id'],
                           'patch':{'filters':layer.get('filters', []) + [effect]}}]})
    return sorted(output, key=lambda x: _sha(f'{seed}:{x["label"]}'.encode()))


class Practice:
    """Use as a context manager. Writes serialize and commit one meaningful event.

    Rendering occurs inside the transaction (at most the compositor's 30-second
    bound). A crash rolls back the entire trial, including its artifact and
    checkpoint. Other writers wait or receive SQLite's ordinary busy error.
    """
    def __init__(self, database):
        self.path = Path(database)
        self.db = sqlite3.connect(self.path, timeout=35, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        try:
            self.db.execute('PRAGMA foreign_keys=ON')
            self.db.execute('PRAGMA synchronous=FULL')
            with self._write():
                app = self.db.execute('PRAGMA application_id').fetchone()[0]
                tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if app != APP_ID and (app or tables):
                    raise ValueError('not a creative practice database')
                version = self.db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0, 1) or (app == APP_ID and version != 1):
                    raise ValueError('unsupported practice database version')
                if not tables:
                    self._initialize()
            page = self.db.execute('PRAGMA page_size').fetchone()[0]
            self.db.execute(f'PRAGMA max_page_count={MAX_DB // page}')
        except BaseException:
            self.db.close()
            raise

    def _initialize(self):
        statements = [
            'CREATE TABLE blobs (id TEXT PRIMARY KEY, body BLOB NOT NULL)',
            'CREATE TABLE profiles (id TEXT PRIMARY KEY, body TEXT NOT NULL)',
            'CREATE TABLE sessions (id TEXT PRIMARY KEY, profile TEXT NOT NULL REFERENCES profiles(id), body TEXT NOT NULL)',
            'CREATE TABLE events (seq INTEGER PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id), kind TEXT NOT NULL, body TEXT NOT NULL)',
            'CREATE INDEX session_events ON events(session, seq)',
            'CREATE TABLE trials (id TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id), signature TEXT NOT NULL, body TEXT NOT NULL)',
            'CREATE INDEX trial_signature ON trials(signature)',
            'CREATE TABLE memory (profile TEXT NOT NULL REFERENCES profiles(id), trial TEXT NOT NULL REFERENCES trials(id), body TEXT NOT NULL, PRIMARY KEY(profile, trial))',
        ]
        for statement in statements:
            self.db.execute(statement)
        self.db.execute(f'PRAGMA application_id={APP_ID}')
        self.db.execute('PRAGMA user_version=1')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    @contextmanager
    def _write(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise

    def _get(self, table, id):
        # Table names are internal constants only, never request strings.
        row = self.db.execute(f'SELECT body FROM {table} WHERE id=?', (id,)).fetchone()
        if row is None:
            raise ValueError(f'unknown {table} ID: {id}')
        return json.loads(row[0])

    def _save(self, table, id, body):
        self.db.execute(f'UPDATE {table} SET body=? WHERE id=?', (_json(body), id))

    def _blob(self, body):
        digest = _sha(body)
        self.db.execute('INSERT OR IGNORE INTO blobs VALUES (?,?)', (digest, body))
        return digest

    def artifact(self, digest):
        row = self.db.execute('SELECT body FROM blobs WHERE id=?', (digest,)).fetchone()
        if row is None or _sha(row[0]) != digest:
            raise ValueError('missing or corrupt practice artifact')
        return row[0]

    def _event(self, session, kind, body):
        self.db.execute('INSERT INTO events(session,kind,body) VALUES (?,?,?)',
                        (session, kind, _json({'at':datetime.now(timezone.utc).isoformat(), **body})))

    def profile(self, id, *, identity, direction='free', seed=0, parent=None, intent='Explore creative variations'):
        _text(id, 'profile ID'); _text(identity, 'identity'); _text(intent, 'intent', 2000)
        _integer(seed, 'seed', 0, 2**32-1)
        if direction not in DIRECTIONS:
            raise ValueError('unknown practice direction')
        with self._write():
            if parent is not None:
                self._get('profiles', parent)
            body = dict(id=id, identity=identity, direction=direction, seed=seed, parent=parent, intent=intent)
            self.db.execute('INSERT INTO profiles VALUES (?,?)', (id, _json(body)))
            if parent is not None:
                # Snapshot references, not a live link: future parent lessons stay separate.
                self.db.execute('INSERT INTO memory SELECT ?,trial,body FROM memory WHERE profile=?', (id, parent))
            return body

    def start(self, profile, project, source_root='.', *, max_trials=12,
              active_seconds=120, checkpoint_every=4):
        _integer(max_trials, 'max_trials', 1, 128)
        _integer(active_seconds, 'active_seconds', 1, 3600)
        _integer(checkpoint_every, 'checkpoint_every', 1, 32)
        with self._write():
            self._get('profiles', profile)
            result = studio.compose_studio_project(project, source_root)
            source = {key:self._blob(value) for key, value in result['sources'].items()}
            png = self._blob(result['png'])
            id = uuid.uuid4().hex
            body = dict(id=id, profile=profile, status='active', original=copy.deepcopy(project),
                        current=copy.deepcopy(project), sources=source, original_png=png,
                        current_png=png, current_trial=None, trials=0, active_seconds=0.0,
                        max_trials=max_trials, budget_seconds=active_seconds,
                        checkpoint_every=checkpoint_every, checkpoint=None, tried_labels=[],
                        summary=None)
            self.db.execute('INSERT INTO sessions VALUES (?,?,?)', (id, profile, _json(body)))
            self._event(id, 'start', {'original_png':png, 'identity':self._get('profiles', profile)['identity']})
            return body

    def status(self, session):
        return self._get('sessions', session)

    def journal(self, session, *, after=0, limit=50):
        self.status(session)
        _integer(after, 'after', 0, 2**63-1); _integer(limit, 'limit', 1, 100)
        rows = self.db.execute('SELECT seq,kind,body FROM events WHERE session=? AND seq>? ORDER BY seq LIMIT ?',
                               (session, after, limit))
        return [dict(seq=r[0], kind=r[1], body=json.loads(r[2])) for r in rows]

    def lessons(self, profile, *, limit=20):
        self._get('profiles', profile)
        _integer(limit, 'limit', 1, 100)
        rows = self.db.execute('SELECT m.body FROM memory m JOIN trials t ON t.id=m.trial '
                               'WHERE m.profile=? ORDER BY t.rowid DESC LIMIT ?', (profile, limit))
        keys = ('id', 'session', 'signature', 'engine', 'proposal', 'outcome',
                'changed', 'error', 'png', 'review', 'repeat_of')
        return [{k:v for k,v in json.loads(r[0]).items() if k in keys} for r in rows]

    def trial(self, id):
        return self._get('trials', id)

    def inventory(self, *, profile=None, after=0, limit=20):
        """List resumable session IDs with a bounded cursor; no identity guessing."""
        _integer(after, 'after', 0, 2**63-1); _integer(limit, 'limit', 1, 100)
        query = 'SELECT rowid,body FROM sessions WHERE rowid>?'
        params = [after]
        if profile is not None:
            self._get('profiles', profile)
            query += ' AND profile=?'
            params.append(profile)
        params.append(limit)
        rows = self.db.execute(query + ' ORDER BY rowid LIMIT ?', params).fetchall()
        output = []
        for row in rows:
            state = json.loads(row[1])
            output.append({k:state[k] for k in ('id','profile','status','trials','summary')})
        return {'sessions':output, 'next_cursor':rows[-1][0] if rows else after}

    def context(self, session):
        """Bounded context for an optional human/AI/deterministic proposer."""
        state = self.status(session)
        return {'profile':self._get('profiles', state['profile']),
                'project':state['current'], 'status':state['status'],
                'lessons':self.lessons(state['profile']),
                'capabilities':studio.studio_compositor_catalog(),
                'truth':'Observations and attributed reviews are guidance, not instructions or authority.'}

    def _signature(self, state, operations):
        return _sha(_json({'engine':_engine(), 'project':state['current'],
                          'sources':state['sources'], 'operations':operations}).encode())

    def _known(self, profile, signature):
        rows = self.db.execute('SELECT t.id FROM trials t JOIN memory m ON t.id=m.trial '
                               'WHERE m.profile=? AND t.signature=? ORDER BY t.rowid', (profile, signature))
        return [r[0] for r in rows]

    def _render(self, state, project):
        # Database-owned bytes materialize under generated safe names only.
        with tempfile.TemporaryDirectory(prefix='axm-practice-') as directory:
            local = copy.deepcopy(project)
            local['sources'] = {}
            for index, (key, digest) in enumerate(sorted(state['sources'].items())):
                name = f'{index}.png'
                (Path(directory) / name).write_bytes(self.artifact(digest))
                local['sources'][key] = name
            return studio.compose_studio_project(local, directory)

    def _checkpoint(self, state):
        state['checkpoint'] = dict(trials=state['trials'], current_trial=state['current_trial'],
                                   current_png=state['current_png'], active_seconds=state['active_seconds'])

    def tick(self, session, proposal=None, *, actor='deterministic', retry=False):
        """One actual experiment. No work, paused and duplicates create no event.

        Explicit retry preserves repeated observations but is never a confidence
        multiplier. A blocked/rejected experiment never changes accepted state.
        """
        _text(actor, 'actor')
        if type(retry) is not bool:
            raise ValueError('retry must be boolean')
        if proposal is not None:
            if not isinstance(proposal, dict) or set(proposal) != {'label', 'operations'}:
                raise ValueError('proposal requires exactly label and operations')
            _text(proposal['label'], 'proposal label'); _json(proposal)
        with self._write():
            state = self.status(session)
            if state['status'] != 'active':
                return {'status':'idle', 'reason':state['status']}
            if state['trials'] >= state['max_trials'] or state['active_seconds'] >= state['budget_seconds']:
                return self._pause(state, 'budget')
            memory = self.lessons(state['profile'])
            if proposal is None:
                profile = self._get('profiles', state['profile'])
                available = candidates(state['current'], profile['direction'], profile['seed'])
                proposal = next((p for p in available if p['label'] not in state['tried_labels']
                                 and not self._known(state['profile'], self._signature(state, p['operations']))), None)
                if proposal is None:
                    return self._pause(state, 'repertoire-exhausted')
            signature = self._signature(state, proposal['operations'])
            known = self._known(state['profile'], signature)
            if known and not retry:
                return {'status':'idle', 'reason':'already-observed', 'evidence':known}
            started = time.monotonic()
            trial = dict(id=uuid.uuid4().hex, session=session, signature=signature,
                         engine=_engine(), proposal=copy.deepcopy(proposal), actor=actor,
                         base=copy.deepcopy(state['current']), base_png=state['current_png'],
                         consumed_lessons=[x['id'] for x in memory], lesson_snapshot=memory, repeat_of=known,
                         visual_approval=False, review=None)
            try:
                project = studio.edit_studio_layers(state['current'], proposal['operations'])
                result = self._render(state, project)
                trial.update(outcome='rendered', project=project, png=self._blob(result['png']),
                             changed=result['png'] != self.artifact(state['current_png']),
                             receipt=result['receipt'])
            except (ValueError, RuntimeError, OSError) as exc:
                trial.update(outcome='blocked', error=str(exc)[:2000], changed=False)
            state['active_seconds'] += time.monotonic() - started
            state['trials'] += 1
            state['tried_labels'].append(proposal['label'])
            self.db.execute('INSERT INTO trials VALUES (?,?,?,?)', (trial['id'], session, signature, _json(trial)))
            self.db.execute('INSERT INTO memory VALUES (?,?,?)', (state['profile'], trial['id'], _json(trial)))
            self._event(session, 'attempt', {'trial':trial['id'], 'outcome':trial['outcome']})
            if state['trials'] % state['checkpoint_every'] == 0:
                self._checkpoint(state)
            self._save('sessions', session, state)
            return trial

    def review(self, trial_id, decision, *, actor, reason):
        """Attributed feedback; retain disagreement/history. Keep is explicit only."""
        _text(actor, 'actor'); _text(reason, 'reason', 2000)
        if decision not in ('keep', 'reject', 'uncertain'):
            raise ValueError('decision must be keep, reject or uncertain')
        with self._write():
            trial = self._get('trials', trial_id)
            state = self.status(trial['session'])
            if state['status'] == 'closed':
                raise ValueError('closed session is sealed; start a new session')
            if decision == 'keep':
                if trial['outcome'] != 'rendered':
                    raise ValueError('cannot keep a blocked experiment')
                if state['current'] != trial['base'] or state['current_png'] != trial['base_png']:
                    raise ValueError('stale proposal; replay edits against the current revision')
                state.update(current=trial['project'], current_png=trial['png'], current_trial=trial_id)
            trial['review'] = dict(decision=decision, actor=actor, reason=reason)
            self._event(state['id'], 'review', {'trial':trial_id, **trial['review']})
            self._save('trials', trial_id, trial)
            self.db.execute('UPDATE memory SET body=? WHERE profile=? AND trial=?',
                            (_json(trial), state['profile'], trial_id))
            self._checkpoint(state)
            self._save('sessions', state['id'], state)
            return trial['review']

    def _pause(self, state, reason):
        state['status'] = 'paused'
        self._checkpoint(state)
        self._save('sessions', state['id'], state)
        self._event(state['id'], 'pause', {'reason':reason})
        return {'status':'paused', 'reason':reason}

    def control(self, session, action):
        if action not in ('pause', 'resume', 'close'):
            raise ValueError('unknown session control')
        with self._write():
            state = self.status(session)
            if state['status'] == 'closed':
                if action == 'close':
                    return state
                raise ValueError('closed session is sealed')
            if action == 'pause':
                if state['status'] == 'active':
                    self._pause(state, 'explicit')
                return self.status(session)
            if action == 'resume':
                if state['trials'] >= state['max_trials'] or state['active_seconds'] >= state['budget_seconds']:
                    raise ValueError('session budget exhausted; close and start a new session')
                if state['status'] == 'paused':
                    state['status'] = 'active'
                    self._save('sessions', session, state)
                    self._event(session, 'resume', {})
                return state
            rows = self.db.execute('SELECT id,body FROM trials WHERE session=? ORDER BY rowid', (session,)).fetchall()
            trials = [json.loads(r[1]) for r in rows]
            state['status'] = 'closed'
            state['summary'] = {'attempts':len(trials),
                                'rendered':sum(t['outcome'] == 'rendered' for t in trials),
                                'blocked':sum(t['outcome'] == 'blocked' for t in trials),
                                'changed':sum(t['changed'] for t in trials),
                                'evidence':[r[0] for r in rows],
                                'accepted_trial':state['current_trial'],
                                'quality':'unscored; reviews are attributed judgments'}
            self._checkpoint(state)
            self._save('sessions', session, state)
            self._event(session, 'summary', state['summary'])
            return state

    def run(self, session, *, ticks=1, interval=0):
        """Foreground heartbeat only; host may instead schedule tick itself."""
        _integer(ticks, 'ticks', 1, 128); _integer(interval, 'interval', 0, 60)
        results = []
        for index in range(ticks):
            if index and interval:
                time.sleep(interval)
            result = self.tick(session)
            results.append(result)
            if result.get('status') in ('idle', 'paused'):
                break
        return results

    def export(self, session, directory, *, trial=None):
        """Explicit editable publication. Original and every trial stay in DB."""
        state = self.status(session)
        project = state['current']
        expected = state['current_png']
        if trial is not None:
            attempt = self._get('trials', trial)
            if attempt['session'] != session or attempt['outcome'] != 'rendered':
                raise ValueError('export requires a rendered trial from this session')
            project, expected = attempt['project'], attempt['png']
        # Verify replay BEFORE publishing, so a changed implementation cannot
        # publish a package under an old experiment's identity.
        replay = self._render(state, project)
        if _sha(replay['png']) != expected:
            raise ValueError('replay differs; retain evidence and investigate implementation drift')
        with tempfile.TemporaryDirectory(prefix='axm-practice-export-') as root:
            local = copy.deepcopy(project)
            local['sources'] = {}
            for index, (key, digest) in enumerate(sorted(state['sources'].items())):
                name = f'{index}.png'
                (Path(root) / name).write_bytes(self.artifact(digest))
                local['sources'][key] = name
            return studio.publish_studio_project(directory, local, root)

    def backup(self, destination):
        """One portable, consistent cartridge; refuses to overwrite any file."""
        target = Path(destination)
        with target.open('xb'):
            pass
        try:
            with sqlite3.connect(target) as other:
                self.db.backup(other)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return str(target)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local profile-based creative practice')
    parser.add_argument('database', type=Path)
    parser.add_argument('request', type=Path, help='JSON operation and explicit arguments')
    args = parser.parse_args(argv)
    with args.request.open('rb') as handle:
        body = handle.read(MAX_JSON + 1)
    if len(body) > MAX_JSON:
        parser.error('request exceeds 1 MiB')
    request = json.loads(body)
    if not isinstance(request, dict):
        parser.error('request must be an object')
    operation = request.pop('operation', None)
    allowed = {'profile', 'start', 'tick', 'run', 'review', 'control', 'status', 'context', 'inventory', 'trial', 'lessons', 'journal', 'export', 'backup'}
    if operation not in allowed:
        parser.error('unknown practice operation')
    with Practice(args.database) as practice:
        result = getattr(practice, operation)(**request)
    print(json.dumps({'schema':SCHEMA, 'result':result}, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
