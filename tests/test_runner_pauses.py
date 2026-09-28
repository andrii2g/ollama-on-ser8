"""Check pause scheduling and cleanup without suspending a real process."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from runner_pauses import RunnerPauses


class RunnerPausesTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.clock = patch('runner_pauses.time.monotonic', return_value=0).start()
        self.addCleanup(patch.stopall)
        # Bypass Windows runner discovery: these tests exercise policy and cleanup.
        self.controller = RunnerPauses.__new__(RunnerPauses)
        self.controller.directory = Path(self.folder.name)
        self.controller.pid = 123
        self.controller.work_seconds = 300
        self.controller.rest_seconds = 120
        self.controller.pause_at = 85
        self.controller.resume_below = 70
        self.controller.active_since = self.controller.started = 0
        self.controller.paused = False
        self.controller.disabled = False
        self.controller.events = []
        self.controller.command = MagicMock()
        self.controller.kernel = MagicMock()
        self.controller.handle = 456

    def test_scheduled_pause_resumes_same_controller_after_two_minutes(self):
        c = self.controller
        self.clock.return_value = 299
        c.tick(65)
        c.command.assert_not_called()
        self.clock.return_value = 300
        c.tick(65)
        c.command.assert_called_once_with()
        self.clock.return_value = 419
        c.tick(50)
        self.assertTrue(c.paused)
        self.clock.return_value = 420
        c.tick(50)
        c.command.assert_called_with(resume=True)
        self.assertFalse(c.paused)
        state = json.loads((c.directory / 'pauses.json').read_text())
        self.assertEqual(state['runner_pid'], 123)
        self.assertEqual(state['events'][0]['duration_sec'], 120)
        self.assertEqual(state['events'][0]['reason'], 'scheduled')
        self.clock.return_value = 719
        c.tick(65)
        self.assertFalse(c.paused)
        self.clock.return_value = 720
        c.tick(65)
        self.assertTrue(c.paused)

    def test_thermal_pause_waits_for_cooling_even_after_rest(self):
        c = self.controller
        self.clock.return_value = 180
        c.tick(85)
        self.assertEqual(c.events[0]['reason'], 'temperature')
        self.clock.return_value = 300
        c.tick(70)
        self.assertTrue(c.paused)
        self.clock.return_value = 305
        c.tick(69)
        self.assertFalse(c.paused)

    def test_cleanup_resumes_runner_without_waiting_for_schedule(self):
        c = self.controller
        c.tick(85)
        self.clock.return_value = 10
        c.close()
        c.command.assert_called_with(resume=True)
        self.assertFalse(c.paused)
        c.kernel.CloseHandle.assert_called_once_with(456)

    def test_temperature_only_mode_preserves_request_through_hot_pause(self):
        c = self.controller
        c.work_seconds = 0
        c.pause_at = 95
        c.resume_below = 80
        c.rest_seconds = 60
        self.clock.return_value = 7200
        c.tick(94)
        c.command.assert_not_called()
        c.tick(95)
        self.assertTrue(c.paused)
        self.assertEqual(c.events[0]['reason'], 'temperature')
        self.clock.return_value = 7259
        c.tick(65)
        self.assertTrue(c.paused)
        self.clock.return_value = 7260
        c.tick(65)
        self.assertFalse(c.paused)
        c.command.assert_called_with(resume=True)

    def test_suspend_failure_does_not_claim_a_pause(self):
        c = self.controller
        c.command.side_effect = RuntimeError('suspend failed')
        with self.assertRaisesRegex(RuntimeError, 'suspend failed'):
            c.tick(85)
        self.assertFalse(c.paused)
        self.assertEqual(c.events, [])

    def test_runtime_override_resumes_and_prevents_new_pauses(self):
        c = self.controller
        c.directory = c.directory / '64k'
        c.directory.mkdir()
        c.tick(85)
        (c.directory.parent / 'NO_PAUSES').touch()
        self.clock.return_value = 5
        c.tick(90)
        self.assertFalse(c.paused)
        self.assertTrue(c.disabled)
        self.clock.return_value = 600
        c.tick(90)
        self.assertFalse(c.paused)
        self.assertEqual(len(c.events), 1)
        (c.directory.parent / 'NO_PAUSES').unlink()
        c.tick(90)
        self.assertTrue(c.paused)
        self.assertFalse(c.disabled)


if __name__ == '__main__':
    unittest.main()
