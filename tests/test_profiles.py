"""Profile selection and verification regression tests; no live server required."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DIGEST = '22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643'
WEIGHT = 'f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d'


def embedded(name):
    return (ROOT / 'scripts' / name).read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]


class FakeAPI:
    def __init__(self, digest=DIGEST, context=131072):
        self.digest = digest
        self.context = context
        self.created = []

    def open(self, request, timeout):
        url = request if isinstance(request, str) else request.full_url
        body = json.loads(request.data) if not isinstance(request, str) and request.data else {}
        if url.endswith('/api/version'):
            value = {'version': '0.34.2'}
        elif url.endswith('/api/tags'):
            value = {'models': [{'name': 'qwen3.8:27b-mtp-q4_K_M', 'digest': self.digest}]}
        elif url.endswith('/api/show'):
            tag = body['model'].split(':')[-1]
            params = ''
            if tag in ('8k', '16k', '32k', '64k', '128k'):
                params = '\n'.join(line.removeprefix('PARAMETER ') for line in (ROOT/'profiles'/('Modelfile.'+tag)).read_text().splitlines() if line.startswith('PARAMETER '))
            value = {'details': {'quantization_level': 'Q4_K_M'}, 'modelfile': WEIGHT,
                     'model_info': {'qwen35.nextn_predict_layers': 1}, 'parameters': params}
        elif url.endswith('/api/ps'):
            value = {'models': [{'name': 'ser8-qwen38:128k', 'context_length': self.context, 'size': 100, 'size_vram': 100}]}
        else:
            raise AssertionError(url)
        return io.BytesIO(json.dumps(value).encode())

    def run(self, args, check):
        self.created.append(args)


class ProfilesTest(unittest.TestCase):
    def execute(self, name, argv, api):
        with patch.object(sys, 'argv', argv), patch('urllib.request.build_opener', return_value=api), patch('subprocess.run', side_effect=api.run), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(compile(embedded(name), name, 'exec'), {})

    def test_create_selected_large_profiles(self):
        api = FakeAPI()
        self.execute('apply-profiles.sh', ['-', str(ROOT), '32k', '64k', '128k'], api)
        self.assertEqual([x[2] for x in api.created], ['ser8-qwen38:32k', 'ser8-qwen38:64k', 'ser8-qwen38:128k'])

    def test_default_selection_remains_8k_and_16k(self):
        api = FakeAPI()
        self.execute('apply-profiles.sh', ['-', str(ROOT)], api)
        self.assertEqual([x[2] for x in api.created], ['ser8-qwen38:8k', 'ser8-qwen38:16k'])

    def test_invalid_profile_does_not_create(self):
        api = FakeAPI()
        with self.assertRaises(SystemExit):
            self.execute('apply-profiles.sh', ['-', str(ROOT), '256k'], api)
        self.assertEqual(api.created, [])

    def test_source_digest_mismatch_does_not_create(self):
        api = FakeAPI(digest='unexpected')
        with self.assertRaises(SystemExit):
            self.execute('apply-profiles.sh', ['-', str(ROOT), '32k'], api)
        self.assertEqual(api.created, [])

    def test_verify_128k(self):
        self.execute('verify-profile.sh', ['-', '128k'], FakeAPI())

    def test_verify_rejects_smaller_allocated_context(self):
        with self.assertRaises(SystemExit):
            self.execute('verify-profile.sh', ['-', '128k'], FakeAPI(context=65536))


if __name__ == '__main__':
    unittest.main()
