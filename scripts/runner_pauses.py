"""Windows-only cooling pauses for one verified Ollama runner using Microsoft PsSuspend."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import time


class RunnerPauses:
    def __init__(self, tool, context, weight, directory, work_seconds=300, rest_seconds=120, pause_at=85, resume_below=70):
        if os.name != 'nt':
            raise RuntimeError('Process pauses currently require Windows')
        self.tool = str(Path(tool).resolve())
        self.directory = directory
        self.work_seconds, self.rest_seconds = work_seconds, rest_seconds
        self.pause_at, self.resume_below = pause_at, resume_below
        self.events = []
        self.paused = False
        self.disabled = False
        self.active_since = time.monotonic()
        self.started = self.active_since
        command = "Get-CimInstance Win32_Process -Filter \"Name='llama-server.exe'\" | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
        raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True)
        runners = json.loads(raw)
        if isinstance(runners, dict):
            runners = [runners]
        matches = [r for r in runners or [] if weight in r['CommandLine'] and f' -c {context} ' in r['CommandLine'] and ' -np 1 ' in r['CommandLine']]
        if len(matches) != 1:
            raise RuntimeError('Cannot identify exactly one benchmark runner')
        self.pid = matches[0]['ProcessId']
        # Holding a handle prevents the PID from being reused while we control it.
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.OpenProcess.restype = ctypes.c_void_p
        self.kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        self.kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = self.kernel.OpenProcess(0x1000 | 0x100000, False, self.pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.persist()

    def persist(self):
        state = {'runner_pid': self.pid, 'paused': self.paused, 'pauses_disabled': self.disabled, 'work_seconds': self.work_seconds, 'rest_seconds': self.rest_seconds, 'pause_at_c': self.pause_at, 'resume_below_c': self.resume_below, 'events': self.events}
        temporary = self.directory / 'pauses.tmp'
        temporary.write_text(json.dumps(state, indent=2)+'\n', encoding='utf-8')
        temporary.replace(self.directory / 'pauses.json')

    def command(self, resume=False):
        status = ctypes.c_uint32()
        if not self.kernel.GetExitCodeProcess(self.handle, ctypes.byref(status)) or status.value != 259:
            raise RuntimeError('Benchmark runner exited')
        args = [self.tool, '-accepteula', '-nobanner'] + (['-r'] if resume else []) + [str(self.pid)]
        result = subprocess.run(args, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('PsSuspend failed: ' + result.stdout + result.stderr)

    def tick(self, temperature):
        disabled = (self.directory.parent / 'NO_PAUSES').exists()
        if disabled != self.disabled:
            self.disabled = disabled
            self.persist()
            print('Cooling pauses ' + ('disabled' if disabled else 'enabled') + ' by NO_PAUSES control file', flush=True)
        if disabled:
            self.resume(temperature)
            return
        now = time.monotonic()
        if not self.paused and (temperature >= self.pause_at or (self.work_seconds > 0 and now-self.active_since >= self.work_seconds)):
            reason = 'temperature' if temperature >= self.pause_at else 'scheduled'
            self.command()
            self.paused = True
            self.events.append({'start_sec': time.monotonic()-self.started, 'temperature_c': temperature, 'reason': reason})
            self.pause_started = time.monotonic()
            self.persist()
            print(f'PAUSE runner {self.pid}: {reason}, GPU {temperature} C; preserving request/context', flush=True)
        elif self.paused and now-self.pause_started >= self.rest_seconds and temperature < self.resume_below:
            self.resume(temperature)

    def resume(self, temperature=None):
        if self.paused:
            self.command(resume=True)
            self.paused = False
            now = time.monotonic()
            self.events[-1].update({'end_sec': now-self.started, 'duration_sec': now-self.pause_started, 'resume_temperature_c': temperature})
            self.active_since = now
            self.persist()
            print(f'RESUME runner {self.pid}: GPU {temperature} C; continuing saved request', flush=True)

    def close(self):
        try:
            self.resume()
        finally:
            self.kernel.CloseHandle(self.handle)
