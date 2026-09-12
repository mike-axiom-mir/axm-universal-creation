import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from axm_uc.cli import build_parser
from axm_uc.rts_polish import polish_workshop


class RTSWorkshopPublicationTests(unittest.TestCase):
    def fixture(self, temp):
        root=Path(temp);script=root/'tools/blender/axm_rts_workshop.py';script.parent.mkdir(parents=True);script.write_text('# fixture')
        font=root/'font.ttf';font.write_bytes(b'fixture-font')
        return root,font

    def test_preflight_preserves_existing_output_and_rejects_unbounded_render(self):
        with tempfile.TemporaryDirectory() as temp:
            root,font=self.fixture(temp);target=root/'out';target.mkdir();(target/'keep').write_text('existing')
            with self.assertRaises(FileExistsError):polish_workshop(root,target,sys.executable,font)
            self.assertEqual((target/'keep').read_text(),'existing')
            for settings in [(255,32),(4096,32),(900,1000),(True,32)]:
                with self.assertRaises(ValueError):polish_workshop(root,root/'new',sys.executable,font,*settings)
            self.assertFalse((root/'new').exists())

    def test_success_exit_without_evidence_cannot_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root,font=self.fixture(temp)
            with patch('axm_uc.rts_polish.subprocess.run',return_value=subprocess.CompletedProcess([],0)):
                with self.assertRaisesRegex(RuntimeError,'verification report'):
                    polish_workshop(root,root/'out',sys.executable,font)
            self.assertFalse((root/'out').exists())

    def test_cli_requires_explicit_runtime_and_font(self):
        args=build_parser().parse_args(['rts-workshop-polish','out','--python','local-python','--font','font.ttf'])
        self.assertEqual((args.python,args.font,args.resolution,args.samples),('local-python','font.ttf',1100,64))

if __name__=='__main__':unittest.main()
