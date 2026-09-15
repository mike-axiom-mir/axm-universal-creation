"""Execute real practice, persistence and feedback; never infer aesthetic quality."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from axm_uc.creative_practice import Practice, candidates, main
from axm_uc import creative_practice as practice_module
from axm_uc import studio_compositor as studio
from axm_uc.fabric_noise import png_bytes


def project():
    return {'schema':studio.SCHEMA, 'sources':{}, 'recipe':{
        'schema':'axm.raster-composition/v1', 'canvas':{'width':8, 'height':8},
        'layers':[{'id':'paint', 'fill':'#4277AD'}]}}


def proposal(effect='invert'):
    return {'label':effect, 'operations':[{'op':'change', 'id':'paint',
            'patch':{'filters':[{'type':effect, 'amount':1}]}}]}


@unittest.skipUnless(shutil.which('node'), 'Node is required; dedicated CI supplies it')
class PracticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'practice.sqlite'
        self.p = Practice(self.file)
        self.addCleanup(self.p.db.close)
        self.p.profile('salvage', identity='AXM-maker', direction='free', seed=471)
        self.s = self.p.start('salvage', project(), checkpoint_every=2)['id']

    def test_real_creation_keep_export_and_source_preservation(self):
        original = copy.deepcopy(self.p.status(self.s)['original'])
        trial = self.p.tick(self.s, proposal())
        self.assertEqual(trial['outcome'], 'rendered')
        self.assertTrue(trial['changed'])
        self.assertFalse(trial['visual_approval'])
        self.assertEqual(self.p.status(self.s)['current'], original)
        self.p.review(trial['id'], 'keep', actor='human:Mike', reason='Useful inverted paint study')
        self.assertEqual(self.p.status(self.s)['current_trial'], trial['id'])
        self.p.export(self.s, self.root / 'editable')
        exported = json.loads((self.root / 'editable/project.json').read_text())
        self.assertEqual(studio.compose_studio_project(exported, self.root / 'editable')['png'],
                         self.p.artifact(trial['png']))
        self.assertEqual(self.p.status(self.s)['original'], original)

    def test_source_bytes_survive_original_file_loss_and_database_backup(self):
        body = png_bytes(8,8,4,bytes([210,75,21,255])*64)
        (self.root / 'ink.png').write_bytes(body)
        source = project(); source['sources']={'ink':'ink.png'}
        source['recipe']['layers']=[{'id':'paint','source_artifact_id':'ink'}]
        session = self.p.start('salvage', source, self.root)['id']
        (self.root / 'ink.png').unlink()
        trial = self.p.tick(session, proposal())
        self.p.review(trial['id'], 'keep', actor='machine:review', reason='Explicit test selection')
        backup = self.root / 'portable.sqlite'
        self.p.backup(backup)
        with self.assertRaises(FileExistsError): self.p.backup(backup)
        with Practice(backup) as recovered:
            recovered.export(session, self.root / 'restored')
            request = json.loads((self.root / 'restored/project.json').read_text())
            self.assertEqual((self.root / 'restored' / request['sources']['ink']).read_bytes(), body)
            self.assertEqual(recovered.artifact(trial['png']), self.p.artifact(trial['png']))

    def test_failed_proposal_is_evidence_not_state_or_improvement(self):
        before = self.p.status(self.s)
        trial = self.p.tick(self.s, proposal('missing-lightning-filter'))
        self.assertEqual(trial['outcome'], 'blocked')
        self.assertIn('unsupported filter', trial['error'])
        self.assertEqual(self.p.status(self.s)['current'], before['current'])
        with self.assertRaises(ValueError):
            self.p.review(trial['id'], 'keep', actor='machine', reason='cannot invent success')
        later = self.p.tick(self.s, proposal('grayscale'))
        self.assertIn(trial['id'], later['consumed_lessons'])

    def test_remembered_attempt_changes_next_session_selection(self):
        first = self.p.tick(self.s)
        self.p.control(self.s, 'close')
        next_session = self.p.start('salvage', project())['id']
        second = self.p.tick(next_session)
        self.assertNotEqual(first['signature'], second['signature'])
        self.assertNotEqual(first['proposal']['label'], second['proposal']['label'])
        self.assertIn(first['id'], second['consumed_lessons'])
        # A fresh profile with the same seed makes the original choice.
        self.p.profile('fresh', identity='AXM-maker', seed=471)
        fresh = self.p.start('fresh', project())['id']
        self.assertEqual(first['signature'], self.p.tick(fresh)['signature'])

    def test_repetition_is_idempotent_unless_explicit_and_never_votes(self):
        first = self.p.tick(self.s, proposal())
        before = self.p.journal(self.s)
        for _ in range(30):
            result = self.p.tick(self.s, proposal())
            self.assertEqual(result['reason'], 'already-observed')
        self.assertEqual(before, self.p.journal(self.s))
        retry = self.p.tick(self.s, proposal(), retry=True)
        self.assertEqual(retry['repeat_of'], [first['id']])
        self.assertFalse(retry['visual_approval'])
        self.assertNotIn('confidence', retry)

    def test_profile_fork_snapshots_feedback_and_keeps_future_learning_separate(self):
        t = self.p.tick(self.s, proposal())
        self.p.review(t['id'], 'uncertain', actor='machine:a', reason='Need visual inspection')
        self.p.profile('graphic', identity='AXM-maker', parent='salvage', direction='graphic')
        self.p.review(t['id'], 'reject', actor='human:Mike', reason='Does not fit this direction')
        self.assertEqual(self.p.lessons('graphic')[0]['review']['decision'], 'uncertain')
        self.assertEqual(self.p.lessons('salvage')[0]['review']['decision'], 'reject')
        child = self.p.start('graphic', project())['id']
        child_trial = self.p.tick(child)
        self.assertNotIn(child_trial['id'], [x['id'] for x in self.p.lessons('salvage')])
        self.assertIn(t['id'], child_trial['consumed_lessons'])

    def test_noop_pixels_are_recorded_as_no_effect(self):
        p = {'label':'unchanged', 'operations':[{'op':'change','id':'paint','patch':{'opacity':1}}]}
        t = self.p.tick(self.s, p)
        self.assertFalse(t['changed'])
        self.assertEqual(t['png'], t['base_png'])
        count = self.p.db.execute('SELECT count(*) FROM blobs').fetchone()[0]
        self.assertEqual(count, 1)

    def test_idle_pause_resume_and_checkpoint_are_bounded(self):
        self.p.tick(self.s, proposal())
        self.assertIsNone(self.p.status(self.s)['checkpoint'])
        self.p.tick(self.s, proposal('grayscale'))
        self.assertEqual(self.p.status(self.s)['checkpoint']['trials'], 2)
        self.p.control(self.s, 'pause')
        before = self.p.journal(self.s)
        for _ in range(100): self.p.tick(self.s)
        self.assertEqual(self.p.journal(self.s), before)
        self.p.control(self.s, 'resume')
        self.assertEqual(self.p.status(self.s)['status'], 'active')
        # No result or journal file for each attempt/tick.
        self.assertEqual([x.name for x in self.root.iterdir()], ['practice.sqlite'])

    def test_restart_resumes_latest_committed_trial_not_only_periodic_checkpoint(self):
        trial = self.p.tick(self.s, proposal())
        with Practice(self.file) as reopened:
            self.assertEqual(reopened.status(self.s)['trials'], 1)
            self.assertIsNone(reopened.status(self.s)['checkpoint'])
            self.assertEqual(reopened.lessons('salvage')[0]['id'], trial['id'])
            self.assertEqual(reopened.tick(self.s, proposal())['reason'], 'already-observed')

    def test_write_failure_rolls_back_trial_blob_memory_and_checkpoint(self):
        before = self.p.status(self.s)
        with patch.object(self.p, '_event', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): self.p.tick(self.s, proposal())
        self.assertEqual(self.p.status(self.s), before)
        self.assertEqual(self.p.lessons('salvage'), [])
        self.assertEqual(self.p.db.execute('SELECT count(*) FROM blobs').fetchone()[0], 1)
        self.assertEqual(self.p.tick(self.s, proposal())['outcome'], 'rendered')

    def test_hard_process_exit_rolls_back_in_progress_work(self):
        code = """import os,sys
from axm_uc.creative_practice import Practice
p=Practice(sys.argv[1])
p._event=lambda *a: os._exit(7)
p.tick(sys.argv[2])
"""
        import os
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
        result = subprocess.run([sys.executable, '-c', code, str(self.file), self.s], env=env)
        self.assertEqual(result.returncode, 7)
        with Practice(self.file) as reopened:
            self.assertEqual(reopened.status(self.s)['trials'], 0)
            self.assertEqual(reopened.lessons('salvage'), [])
            self.assertEqual(reopened.tick(self.s)['outcome'], 'rendered')

    def test_budgets_and_closed_summary_do_not_reset_on_resume(self):
        short = self.p.start('salvage', project(), max_trials=1)['id']
        self.p.tick(short, proposal())
        self.assertEqual(self.p.tick(short)['reason'], 'budget')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'): self.p.control(short, 'resume')
        closed = self.p.control(short, 'close')
        self.assertEqual(closed['summary']['attempts'], 1)
        before = self.p.journal(short)
        self.p.control(short, 'close')
        self.assertEqual(self.p.journal(short), before)
        with self.assertRaises(ValueError): self.p.control(short, 'resume')
        timed = self.p.start('salvage', project(), active_seconds=1)['id']
        with patch.object(practice_module.time, 'monotonic', side_effect=[10,12]):
            self.p.tick(timed, proposal('grayscale'))
        self.assertEqual(self.p.tick(timed)['reason'], 'budget')

    def test_stale_review_cannot_overwrite_accepted_work_and_dissent_is_retained(self):
        a = self.p.tick(self.s, proposal())
        b = self.p.tick(self.s, proposal('grayscale'))
        self.p.review(a['id'], 'keep', actor='machine:a', reason='Chosen exploration branch')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.p.review(b['id'], 'keep', actor='machine:b', reason='Stale competing revision')
        self.p.review(a['id'], 'reject', actor='human:Mike', reason='Disagree; preserve actual accepted revision')
        self.assertEqual(self.p.status(self.s)['current_trial'], a['id'])
        self.assertEqual([e['body']['decision'] for e in self.p.journal(self.s) if e['kind']=='review'], ['keep','reject'])

    def test_repertoire_exhausts_without_endless_ticks_and_inputs_are_checked(self):
        results = self.p.run(self.s, ticks=20)
        self.assertEqual(results[-1]['reason'], 'repertoire-exhausted')
        self.assertEqual(self.p.status(self.s)['trials'], 6)
        for kwargs in ({'max_trials':True},{'active_seconds':0},{'checkpoint_every':100}):
            with self.assertRaises(ValueError): self.p.start('salvage', project(), **kwargs)
        with self.assertRaises(ValueError): self.p.tick(self.s, {'label':'bad'})
        with self.assertRaises(ValueError): self.p.profile('x', identity='x', direction='invented')
        with self.assertRaises(ValueError): self.p.journal(self.s, limit=100000)
        self.assertEqual(len(self.p.journal(self.s, limit=2)), 2)

    def test_corruption_and_wrong_database_fail_closed(self):
        t = self.p.tick(self.s, proposal())
        self.p.db.execute('UPDATE blobs SET body=? WHERE id=?', (b'corrupt', t['png']))
        with self.assertRaises(ValueError): self.p.artifact(t['png'])
        other = self.root / 'other.sqlite'
        with sqlite3.connect(other) as db: db.execute('CREATE TABLE unrelated(x)')
        before = other.read_bytes()
        with self.assertRaises(ValueError): Practice(other)
        self.assertEqual(other.read_bytes(), before)

    def test_concurrent_writers_commit_only_one_matching_attempt(self):
        from concurrent.futures import ThreadPoolExecutor
        def execute():
            with Practice(self.file) as peer:
                return peer.tick(self.s, proposal())
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: execute(), range(2)))
        self.assertEqual(sum(r.get('outcome') == 'rendered' for r in results), 1)
        self.assertEqual(sum(r.get('reason') == 'already-observed' for r in results), 1)
        self.assertEqual(self.p.status(self.s)['trials'], 1)

    def test_database_full_rolls_back_without_losing_old_evidence(self):
        pages = self.p.db.execute('PRAGMA page_count').fetchone()[0]
        self.p.db.execute(f'PRAGMA max_page_count={pages}')
        original_blob = self.p._blob
        def need_space(body):
            original_blob(bytes(range(256)) * 4096)
            return original_blob(body)
        with patch.object(self.p, '_blob', side_effect=need_space):
            with self.assertRaisesRegex(sqlite3.DatabaseError, 'full'):
                self.p.tick(self.s, proposal())
        self.assertEqual(self.p.status(self.s)['trials'], 0)
        self.assertEqual(self.p.lessons('salvage'), [])
        self.assertTrue(self.p.artifact(self.p.status(self.s)['original_png']).startswith(b'\x89PNG'))

    def test_context_feedback_snapshot_and_paginated_resume_inventory(self):
        first = self.p.tick(self.s, proposal())
        self.p.review(first['id'], 'uncertain', actor='machine:a', reason='Inspect the pixels')
        second = self.p.tick(self.s, proposal('grayscale'))
        self.p.review(first['id'], 'reject', actor='human:Mike', reason='Later dissent')
        saved = self.p.trial(second['id'])['lesson_snapshot'][0]
        self.assertEqual(saved['review']['decision'], 'uncertain')
        self.assertEqual(self.p.context(self.s)['profile']['identity'], 'AXM-maker')
        page = self.p.inventory(limit=1)
        self.assertEqual(page['sessions'][0]['id'], self.s)
        self.assertEqual(self.p.inventory(after=page['next_cursor'])['sessions'], [])

    def test_cli_dispatch_uses_same_state(self):
        request = self.root / 'request.json'
        request.write_text(json.dumps({'operation':'tick','session':self.s,'proposal':proposal()}))
        output = io.StringIO()
        with redirect_stdout(output): main([str(self.file), str(request)])
        self.assertEqual(json.loads(output.getvalue())['result']['outcome'], 'rendered')
        self.assertEqual(self.p.status(self.s)['trials'], 1)


if __name__ == '__main__': unittest.main()
