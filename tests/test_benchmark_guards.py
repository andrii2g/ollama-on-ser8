"""Thermal guards and incremental result persistence without GPU work."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('benchmark_context', Path(sys.path[0]) / 'benchmark-context.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class ThermalGuardsTest(unittest.TestCase):
    def test_hot_or_missing_sensor_prevents_request(self):
        for temperature in (85, None):
            with self.subTest(temperature=temperature), tempfile.TemporaryDirectory() as folder:
                connection = MagicMock()
                connection.sock = None
                with patch.object(bench, 'gpu_temperature', return_value=temperature), patch.object(bench, 'memory', return_value={'available_gib': 20, 'total_gib': 60}), patch.object(bench.http.client, 'HTTPConnection', return_value=connection), contextlib.redirect_stdout(io.StringIO()):
                    result, _ = bench.request_run(Path(folder), 'guard', {}, 10, 85)
                connection.request.assert_not_called()
                self.assertTrue(result['error'])

    def test_stream_and_final_metrics_are_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            connection = MagicMock()
            response = MagicMock(status=200)
            response.__iter__.return_value = iter([json.dumps({'thinking': 'internal trace', 'response': '', 'done': False}).encode(), b'{"response":"READY","done":false}\n', json.dumps({'thinking': 'final trace', 'done': True, 'eval_count': 1, 'eval_duration': 1000000000, 'prompt_eval_count': 17}).encode()])
            connection.getresponse.return_value = response
            with patch.object(bench, 'gpu_temperature', return_value=55), patch.object(bench, 'memory', return_value={'available_gib': 20, 'total_gib': 60}), patch.object(bench.http.client, 'HTTPConnection', return_value=connection), contextlib.redirect_stdout(io.StringIO()):
                result, answer = bench.request_run(Path(folder), 'normal', {}, 10, 85)
            self.assertIsNone(result['error'])
            self.assertEqual(answer, 'READY')
            self.assertEqual(result['generation_tok_sec'], 1)
            self.assertEqual(result['thinking_character_count'], len('internal trace') + len('final trace'))
            self.assertEqual(len((Path(folder) / 'normal-stream.jsonl').read_text().splitlines()), 3)
            self.assertNotIn('internal trace', ''.join(path.read_text() for path in Path(folder).iterdir()))
            self.assertNotIn('final trace', ''.join(path.read_text() for path in Path(folder).iterdir()))

    def test_cooldown_waits_for_temperature(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(bench, 'gpu_temperature', side_effect=[75, 65]), patch.object(bench.time, 'sleep') as sleep, contextlib.redirect_stdout(io.StringIO()):
            output = Path(folder) / 'cooldown.json'
            bench.cooldown(output, 0, 70)
            sleep.assert_called_once_with(10)
            self.assertEqual(len(json.loads(output.read_text())), 2)

    def test_cooldown_fails_closed_without_sensor(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(bench, 'gpu_temperature', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'sensor unavailable'):
                bench.cooldown(Path(folder) / 'cooldown.json', 0, 70)


if __name__ == '__main__':
    unittest.main()
