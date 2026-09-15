"""Renderer-free portability of creative dependency pins."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_stickers import Registry, instance
from axm_stickers.core import SCHEMA
from axm_stickers.assembly import CREATIVE, library_bundle, import_library


def definition(id, dependencies=()):
    return {'schema':SCHEMA,'id':id,'version':1,'name':id,'adapter':CREATIVE,
        'attachment':{'space':'2d','socket':'surface','anchor':[0,0]},
        'recipe':{'dependencies':[instance(d,'source')['sticker'] for d in dependencies]},
        'assets':{},'parameters':{},'tags':[],
        'origin':{'author':'AXM','license':'CC0-1.0','source':'Original dependency fixture'}}


class CreativeLibraryTests(unittest.TestCase):
    def test_diamond_dependencies_are_saved_once_and_reimport_without_uc(self):
        with tempfile.TemporaryDirectory() as t, Registry(Path(t)/'a.sqlite') as r, Registry(Path(t)/'b.sqlite') as other:
            a=definition('source');left=definition('left',[a]);right=definition('right',[a]);root=definition('root',[left,right])
            r.register_many([a,left,right,root]);bundle=library_bundle(r,'root',1)
            self.assertEqual(len(bundle['definitions']),4)
            import_library(other,bundle)
            self.assertEqual(library_bundle(other,'root',1),bundle)

    def test_dependency_pin_and_missing_source_fail_without_partial_import(self):
        with tempfile.TemporaryDirectory() as t, Registry(Path(t)/'a.sqlite') as r, Registry(Path(t)/'b.sqlite') as other:
            a=definition('source');root=definition('root',[a]);r.register_many([a,root]);bundle=library_bundle(r,'root',1)
            bad=copy.deepcopy(bundle);bad['definitions'].pop()
            with self.assertRaises(ValueError):import_library(other,bad)
            self.assertEqual(other.search()['entries'],[])
            bad=definition('wrong',[a]);bad['recipe']['dependencies'][0]['digest']='0'*64;r.register(bad)
            with self.assertRaises(ValueError):library_bundle(r,'wrong',1)

    def test_creative_dependency_depth_remains_bounded(self):
        with tempfile.TemporaryDirectory() as t, Registry(Path(t)/'a.sqlite') as r:
            d=definition('source');r.register(d)
            for i in range(15):d=definition('step'+str(i),[d]);r.register(d)
            self.assertEqual(len(library_bundle(r,d['id'],1)['definitions']),16)
            d=definition('too-deep',[d]);r.register(d)
            with self.assertRaisesRegex(ValueError,'deep'):library_bundle(r,'too-deep',1)

    def test_shared_dependency_cannot_hide_a_longer_path(self):
        with tempfile.TemporaryDirectory() as t, Registry(Path(t)/'a.sqlite') as r:
            leaf=definition('leaf'); shared=definition('shared',[leaf]);r.register_many([leaf,shared])
            d=shared
            for i in range(14):d=definition('step'+str(i),[d]);r.register(d)
            # The short branch visits shared first; memoization must retain depth.
            root=definition('root',[shared,d]);r.register(root)
            with self.assertRaisesRegex(ValueError,'deep'):library_bundle(r,'root',1)


if __name__=='__main__':unittest.main()
