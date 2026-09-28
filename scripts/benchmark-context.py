#!/usr/bin/env python3
"""Sequential local Ollama context benchmark; saves requests, responses and memory samples.
Run from the repository root: python scripts/benchmark-context.py --output benchmarks/RUN
Requires the requested profiles to have been created. Does not change server settings.
"""
import argparse
import ctypes
import datetime as dt
import http.client
import json
import os
from pathlib import Path
import re
import socket
import threading
import time
import urllib.request
from gpu_temperature import gpu_temperature
from runner_pauses import RunnerPauses

BASE = 'http://127.0.0.1:11434'
CONTEXTS = {'16k': 16384, '32k': 32768, '64k': 65536, '128k': 131072}
RECORDS = {'16k': 380, '32k': 760, '64k': 1520, '128k': 3040}
WEIGHT = 'f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d'
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': 'application/json'})
    with HTTP.open(req, timeout=30) as response:
        content = response.read()
        return json.loads(content) if content else None


def memory():
    if os.name == 'nt':
        class Status(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ('total', 'available', 'total_page', 'available_page', 'total_virtual', 'available_virtual', 'extended')]
        state = Status()
        state.length = ctypes.sizeof(state)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            raise OSError('GlobalMemoryStatusEx failed')
        return {'available_gib': state.available / 2**30, 'total_gib': state.total / 2**30}
    values = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    return {key: int(values[name].split()[0]) / 2**20 for key, name in [('available_gib', 'MemAvailable'), ('total_gib', 'MemTotal')]}


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def prompt(tag, record_count=None):
    # Distinct markers per size; the answer appears only at the corresponding location.
    codes = {'BEGIN': 'R7M4-K2V9-' + tag, 'MIDDLE': 'P8T3-N6X1-' + tag, 'END': 'W5H2-J9D4-' + tag}
    lines = ['The following records are synthetic reference data.', 'Checkpoint BEGIN has verification code ' + codes['BEGIN'] + '.']
    record_count = RECORDS[tag] if record_count is None else record_count
    for i in range(1, record_count + 1):
        lines.append(f'Record {i:05d}: service=service{i%17}; region=region{i%4}; attempts={i%5}; timeout_ms={1200+i*73}; state=synthetic.')
        if i == record_count // 2:
            lines.append('Checkpoint MIDDLE has verification code ' + codes['MIDDLE'] + '.')
    lines += ['Checkpoint END has verification code ' + codes['END'] + '.', 'Return the verification codes for the three checkpoints from the reference data.', 'Start with exactly three plain-text lines: BEGIN=<code>, MIDDLE=<code>, END=<code> (one per line).', 'Then write about 200 words explaining why timeout values alone cannot establish service reliability and what additional measurements are needed. Do not invent incident facts.']
    return '\n'.join(lines), codes


def request_run(directory, label, body, max_seconds, max_gpu_temp, pause_controller=None):
    save(directory / (label + '-request.json'), body)
    start = time.monotonic()
    conn = http.client.HTTPConnection('127.0.0.1', 11434, timeout=max_seconds + 60)
    finished = threading.Event()
    samples = [{'elapsed_sec': 0, 'gpu_temperature_c': gpu_temperature(), **memory()}]
    state = {'abort': None}

    def monitor():
        low_since = None
        while not finished.is_set():
            elapsed = time.monotonic() - start
            try:
                temperature = gpu_temperature()
            except OSError:
                temperature = None
            sample = {'elapsed_sec': round(elapsed, 2), 'gpu_temperature_c': temperature, **memory()}
            samples.append(sample)
            save(directory / (label + '-memory.json'), samples)
            if sample['available_gib'] < 2:
                low_since = low_since or time.monotonic()
            else:
                low_since = None
            reason = None
            if temperature is None:
                reason = 'GPU temperature sensor unavailable'
            elif temperature >= max_gpu_temp and pause_controller is None:
                reason = f'GPU temperature {temperature:.1f} C reached {max_gpu_temp:.1f} C limit'
            elif (directory.parent / 'STOP').exists():
                reason = 'STOP file requested cancellation'
            elif elapsed > max_seconds:
                reason = 'request time limit'
            elif low_since and time.monotonic() - low_since > 30:
                reason = 'available RAM below 2 GiB for 30 seconds'
            if not reason and pause_controller is not None:
                try:
                    pause_controller.tick(temperature)
                except Exception as exc:
                    reason = 'Pause control failed: ' + str(exc)
            if reason:
                state['abort'] = reason
                while not conn.sock and not finished.wait(0.05):
                    pass
                if conn.sock:
                    try:
                        conn.sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                return
            if len(samples) % 6 == 1:
                print(f'{directory.name}/{label}: {elapsed:.0f}s, available RAM {sample["available_gib"]:.2f} GiB, GPU {temperature} C', flush=True)
            finished.wait(5)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    final = None
    text = ''
    first_token = None
    first_thinking_token = None
    thinking_chars = 0
    thinking_chunks = 0
    error = None
    stream_file = (directory / (label + '-stream.jsonl')).open('w', encoding='utf-8')
    try:
        initial_temp = samples[0]['gpu_temperature_c']
        if initial_temp is None or initial_temp >= max_gpu_temp or state['abort']:
            raise RuntimeError(state['abort'] or 'GPU temperature does not permit starting request')
        conn.request('POST', '/api/generate', json.dumps(body).encode(), {'Content-Type': 'application/json'})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f'HTTP {response.status}: {response.read().decode()}')
        for line in response:
            item = json.loads(line)
            thinking = item.get('thinking', '')
            if thinking:
                thinking_chars += len(thinking)
                thinking_chunks += 1
                if first_thinking_token is None:
                    first_thinking_token = time.monotonic() - start
            # Keep timing/count metrics without persisting the model's reasoning trace.
            stream_file.write(json.dumps({k: v for k, v in item.items() if k != 'thinking'}) + '\n')
            stream_file.flush()
            if item.get('error'):
                raise RuntimeError(item['error'])
            piece = item.get('response', '')
            if piece and first_token is None:
                first_token = time.monotonic() - start
            text += piece
            if item.get('done'):
                final = item
        if not final:
            raise RuntimeError('stream ended without a final response')
    except KeyboardInterrupt:
        error = 'interrupted by user'
    except Exception as exc:
        error = str(exc)
    finally:
        finished.set()
        stream_file.close()
        conn.close()
        monitor_thread.join(timeout=20)
        if pause_controller is not None:
            pause_controller.resume()
    result = {'wall_sec': time.monotonic() - start, 'time_to_first_token_sec': first_token,
              'minimum_available_gib': min(x['available_gib'] for x in samples),
              'maximum_gpu_temperature_c': max((x['gpu_temperature_c'] for x in samples if x['gpu_temperature_c'] is not None), default=None),
              'error': state['abort'] or error, 'first_thinking_token_sec': first_thinking_token,
              'thinking_character_count': thinking_chars, 'thinking_chunk_count': thinking_chunks}
    if pause_controller is not None:
        result['pause_count'] = len(pause_controller.events)
        result['paused_sec'] = sum(e.get('duration_sec', 0) for e in pause_controller.events)
        result['timings_include_cooling_pauses'] = True
    if final:
        final.pop('thinking', None)
        final['response'] = text
        save(directory / (label + '-response.json'), final)
        result.update({k: final.get(k) for k in ('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count', 'done_reason')})
        result['prefill_sec'] = final.get('prompt_eval_duration', 0) / 1e9
        result['generation_tok_sec'] = final['eval_count'] * 1e9 / final['eval_duration'] if final.get('eval_duration') else None
        result['load_sec'] = final.get('load_duration', 0) / 1e9
    (directory / (label + '-response.txt')).write_text(text, encoding='utf-8')
    save(directory / (label + '-memory.json'), samples)
    save(directory / (label + '-result.json'), result)
    print(label + ' result: ' + json.dumps(result), flush=True)
    return result, text


def cooldown(output, seconds, resume_below):
    start = time.monotonic()
    samples = []
    while True:
        temperature = gpu_temperature()
        elapsed = time.monotonic() - start
        samples.append({'elapsed_sec': elapsed, 'gpu_temperature_c': temperature})
        save(output, samples)
        if temperature is None:
            raise RuntimeError('Cannot resume: GPU temperature sensor unavailable')
        if (output.parent / 'STOP').exists():
            raise RuntimeError('STOP file requested cancellation')
        if elapsed >= seconds and temperature < resume_below:
            return
        print(f'Cooldown: {elapsed:.0f}/{seconds}s, GPU {temperature:.1f} C; require below {resume_below:.1f} C', flush=True)
        time.sleep(10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profiles', nargs='+', choices=CONTEXTS, default=['32k', '64k', '128k'])
    parser.add_argument('--records', type=int, help='Override synthetic record count (single profile only)')
    parser.add_argument('--max-seconds', type=int, default=5400, help='Per-request time limit (default 90 minutes)')
    parser.add_argument('--pause-tool', type=Path, help='Windows PsSuspend executable; preserve request during cooling pauses')
    parser.add_argument('--work-seconds', type=int, default=300, help='Interval between scheduled pauses; 0 uses temperature-triggered pauses only')
    parser.add_argument('--rest-seconds', type=int, default=120)
    parser.add_argument('--cooldown-seconds', type=int, default=300)
    parser.add_argument('--max-gpu-temp', type=float, default=85)
    parser.add_argument('--resume-below', type=float, default=70)
    parser.add_argument('--think', choices=('false', 'low', 'medium', 'high'), default='false', help='Thinking mode for long requests; smoke request always has thinking off')
    parser.add_argument('--num-predict', type=int, default=256, help='Maximum combined thinking and answer tokens for each request')
    args = parser.parse_args()
    if args.cooldown_seconds < 0 or not 0 < args.resume_below < args.max_gpu_temp or args.max_seconds <= 0 or args.num_predict <= 0:
        parser.error('invalid time or temperature limits')
    if gpu_temperature() is None:
        parser.error('GPU temperature sensor unavailable; cannot run guarded test')
    if args.work_seconds < 0 or args.rest_seconds < 60:
        parser.error('work seconds must be nonnegative and rests at least 60 seconds')
    if args.pause_tool and (os.name != 'nt' or not args.pause_tool.is_file()):
        parser.error('pause tool must exist on Windows')
    if args.output.exists():
        parser.error('output directory must be new to preserve previous results')
    if args.records is not None and (args.records <= 0 or len(args.profiles) != 1):
        parser.error('--records must be positive and used with exactly one profile')
    if api('/api/ps')['models']:
        parser.error('unload existing models and finish other requests before benchmarking')
    for tag in args.profiles:
        info = api('/api/show', {'model': 'ser8-qwen38:' + tag})
        if WEIGHT not in info.get('modelfile', ''):
            parser.error('unexpected model weights for ' + tag)
        for name, value in {'num_ctx': CONTEXTS[tag], 'num_thread': 6, 'num_batch': 256, 'draft_num_predict': 2, 'temperature': 0}.items():
            if not re.search(rf'(?m)^{name}\s+{value}(?:\.0+)?\s*$', info['parameters']):
                parser.error(f'unexpected {name} for {tag}')
    args.output.mkdir(parents=True)
    run_records = dict(RECORDS)
    if args.records is not None:
        run_records[args.profiles[0]] = args.records
    save(args.output / 'settings.json', {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'ollama': api('/api/version'), 'profiles': args.profiles, 'contexts': CONTEXTS, 'records': run_records, 'memory_before': memory(), 'max_seconds': args.max_seconds, 'cooldown_seconds': args.cooldown_seconds, 'max_gpu_temp_c': args.max_gpu_temp, 'resume_below_c': args.resume_below, 'pause_mode': bool(args.pause_tool), 'work_seconds': args.work_seconds, 'rest_seconds': args.rest_seconds, 'think': args.think, 'num_predict': args.num_predict, 'source_weight': WEIGHT, 'note': 'One smoke request with thinking off and one long request with the selected think setting per profile. Thinking and answer share num_predict. Reasoning trace text is discarded; count and timing metrics are retained. Unload after each profile. Shared-memory GPU; available RAM is whole-system, sampled every 5 seconds.'})
    for tag in args.profiles:
        cooldown(args.output / (tag + '-cooldown.json'), args.cooldown_seconds, args.resume_below)
        directory = args.output / tag
        directory.mkdir()
        model = 'ser8-qwen38:' + tag
        body = {'model': model, 'prompt': 'Reply with exactly READY.', 'stream': True, 'think': False, 'keep_alive': '15m', 'options': {'seed': 42, 'temperature': 0, 'num_predict': 8, 'num_ctx': CONTEXTS[tag]}}
        try:
            smoke, _ = request_run(directory, 'smoke', body, min(args.max_seconds, 600), args.max_gpu_temp)
            placement = api('/api/ps')
            save(directory / 'smoke-placement.json', placement)
            if smoke['error']:
                break
            loaded = next((m for m in placement['models'] if m['name'] == model), None)
            if not loaded or loaded.get('context_length') != CONTEXTS[tag]:
                save(directory / 'skipped.json', {'reason': 'requested context was not allocated'})
                continue
            text, codes = prompt(tag, run_records[tag])
            think = False if args.think == 'false' else args.think
            body = {**body, 'think': think, 'prompt': text, 'options': {**body['options'], 'num_predict': args.num_predict}}
            pause_controller = RunnerPauses(args.pause_tool, CONTEXTS[tag], WEIGHT, directory, args.work_seconds, args.rest_seconds, args.max_gpu_temp, args.resume_below) if args.pause_tool else None
            try:
                result, answer = request_run(directory, 'long', body, args.max_seconds, args.max_gpu_temp, pause_controller)
            finally:
                if pause_controller is not None:
                    pause_controller.close()
            result['retrieval'] = {k: bool(re.search(rf'(?m)^\s*{k}\s*=\s*{re.escape(v)}\s*$', answer)) for k, v in codes.items()}
            result['near_context_target'] = (0.80 * CONTEXTS[tag] <= result.get('prompt_eval_count', 0) <= 0.96 * CONTEXTS[tag]) if not result['error'] else False
            result['input_plus_output_within_context'] = (result.get('prompt_eval_count', 0) + result.get('eval_count', 0) <= CONTEXTS[tag]) if not result['error'] else None
            save(directory / 'long-result.json', result)
            save(directory / 'long-placement.json', api('/api/ps'))
            if result['error']:
                break
        finally:
            try:
                api('/api/generate', {'model': model, 'keep_alive': 0})
            except Exception as exc:
                print('Unload failed: ' + str(exc), flush=True)
                raise



if __name__ == '__main__':
    main()
