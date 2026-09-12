import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from axm_uc.machine import UniversalCreationMachine
from axm_uc.media_workbench import (PaintedMetalSpec, metal_fields, metal_request,
                                    label_request, normalize_wav, wav_request)

ROOT = Path(__file__).resolve().parents[1]

def wav_bytes(raw, width=2, channels=1, rate=8000):
    out = io.BytesIO()
    with wave.open(out, 'wb') as f:
        f.setnchannels(channels); f.setsampwidth(width); f.setframerate(rate); f.writeframes(raw)
    return out.getvalue()

def samples(data):
    with wave.open(io.BytesIO(data)) as f:
        raw = f.readframes(f.getnframes())
    return struct.unpack('<'+'h'*(len(raw)//2), raw)

class MediaWorkbenchTests(unittest.TestCase):
    def test_metal_donor_vectors_and_orm(self):
        fields = metal_fields(32, 7)
        expected = json.loads(Path(__file__).with_name('metal_donor_vectors.json').read_text())
        self.assertEqual({k:hashlib.sha256(v[1]).hexdigest() for k,v in fields.items()}, expected)
        self.assertEqual(fields, metal_fields(32, 7))
        self.assertNotEqual(fields['base_color'], metal_fields(32, 8)['base_color'])
        orm=fields['orm'][1]
        for i,key in enumerate(('ao','roughness','metallic')):
            self.assertEqual(orm[i::3], fields[key][1])
        flat=metal_fields(16, 1, PaintedMetalSpec(normal_strength=0))
        self.assertEqual(flat['normal'][1], bytes((128,128,255))*256)

    def test_label_alpha_and_glyph_fallback(self):
        # Test the actual integrated label PNG without needing an image library.
        import zlib
        request=label_request('unused', 'A', scale=1, padding=0)
        png=base64.b64decode(request['inputs']['binary_files']['label.png']['content'])
        self.assertEqual(struct.unpack('>II',png[16:24]), (5,7))
        self.assertEqual(png[25],6) # RGBA, not opaque RGB
        pos=8; compressed=b''
        while pos<len(png):
            n=struct.unpack('>I',png[pos:pos+4])[0]
            if png[pos+4:pos+8]==b'IDAT':compressed+=png[pos+8:pos+8+n]
            pos+=12+n
        rows=zlib.decompress(compressed)
        alpha=[rows[y*21+1+3:y*21+21:4] for y in range(7)]
        self.assertEqual(alpha[0], bytes((0,255,255,255,0)))
        self.assertEqual(alpha[3], bytes((255,)*5))
        r=label_request('unused','A🙂')
        self.assertEqual(json.loads(r['inputs']['text_files']['media.json'])['unsupported_glyphs'], ['🙂'])

    def test_wav_sample_widths_channel_policy_and_resampling(self):
        for width,raw in [(1,bytes((0,128,255))),
                          (2,struct.pack('<hhh',-32768,0,32512)),
                          (3,b'\x00\x00\x80\x00\x00\x00\x00\x00\x7f'),
                          (4,struct.pack('<iii',-2147483648,0,2130706432))]:
            out,ev=normalize_wav(wav_bytes(raw,width),8000,1)
            self.assertEqual(samples(out),(-32768,0,32512))
            self.assertEqual(ev['source_sample_width'],width)
        source=wav_bytes(struct.pack('<hhhh',100,300,-100,-300),channels=2)
        mono,_=normalize_wav(source,16000,1)
        self.assertEqual(samples(mono),(200,200,-200,-200))
        stereo,_=normalize_wav(wav_bytes(struct.pack('<hh',23,-23)),8000,2)
        self.assertEqual(samples(stereo),(23,23,-23,-23))
        self.assertEqual(normalize_wav(source),normalize_wav(source))

    def test_reject_invalid_before_allocation(self):
        for call in [lambda:metal_fields(True), lambda:metal_fields(1024),
                     lambda:metal_fields(16,1,PaintedMetalSpec(wear=float('nan'))),
                     lambda:metal_fields(16,1,PaintedMetalSpec(scratches=1.2)),
                     lambda:label_request('x','x'*1024,16),
                     lambda:label_request('x','A',True),
                     lambda:normalize_wav(b'not a WAV file'),
                     lambda:normalize_wav(wav_bytes(b'\x00\x00')[:-1]),
                     lambda:normalize_wav(wav_bytes(b'\x00\x00'),True)]:
            with self.assertRaises(ValueError):call()
        huge=bytearray(wav_bytes(b'\x00\x00'));huge[40:44]=struct.pack('<I',0x7ffffffe)
        with self.assertRaises(ValueError):normalize_wav(bytes(huge))

    def test_all_three_machine_paths_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            m=UniversalCreationMachine(ROOT)
            requests=[metal_request(Path(td)/'metal',16,3), label_request(Path(td)/'label','CORE ONLINE'),
                      wav_request(Path(td)/'audio',wav_bytes(struct.pack('<hh',100,-100)),8000,2)]
            for request in requests:
                result=m.create(request); self.assertEqual(result['type'],'CREATION_RESULT',result)
                p=Path(request['inputs']['path']); manifest=json.loads((p/'media.json').read_text())
                for name,info in manifest['files'].items():
                    self.assertEqual(hashlib.sha256((p/name).read_bytes()).hexdigest(),info['sha256'])
                self.assertNotEqual(m.create(request)['type'],'CREATION_RESULT')
