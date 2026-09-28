#!/usr/bin/env python3
"""Compare Ollama thinking effort levels across SER8 context profiles."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New output directory for all effort levels')
    parser.add_argument('--pause-tool', type=Path, required=True, help='Microsoft Sysinternals PsSuspend executable (Windows)')
    parser.add_argument('--num-predict', type=int, default=4096, help='Shared thinking plus answer token cap')
    parser.add_argument('--max-seconds', type=int, default=5400, help='Per-request time limit')
    parser.add_argument('--resume', action='store_true', help='Continue in an existing run directory, retaining completed results')
    args = parser.parse_args()
    if args.output.exists() and not args.resume:
        parser.error('output directory must be new to preserve previous runs')
    if args.resume and not args.output.is_dir():
        parser.error('--resume requires an existing run directory')
    if not args.pause_tool.is_file():
        parser.error('pause tool must exist')
    if args.num_predict <= 0 or args.max_seconds <= 0:
        parser.error('token and time limits must be positive')
    args.output.mkdir(parents=True, exist_ok=True)
    profiles = {'16k': 304, '32k': 720, '64k': 1505, '128k': 3000}
    summary = {'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'profiles_records': profiles, 'levels': ['medium', 'high'], 'num_predict': args.num_predict, 'thermal_policy': {'pause_at_c': 95, 'rest_seconds': 60, 'resume_below_c': 80, 'scheduled_pauses': False}, 'note': 'Within each profile, medium and high receive identical synthetic retrieval prompts. Input lengths target approximately 70-87% of allocated context, preserving output space for thinking and a final answer. Thinking trace text is discarded; only timing and character/chunk counts are saved.', 'results': {}}
    summary_path = args.output / 'summary.json'
    if args.resume and summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        summary.pop('error', None)
        summary.pop('finished_utc', None)
    script = Path(__file__).with_name('benchmark-context.py')
    failed = False
    for profile, records in profiles.items():
        summary['results'][profile] = {}
        for level in summary['levels']:
            output = args.output / profile / level
            result_path = output / profile / 'long-result.json'
            if args.resume and result_path.is_file():
                result = json.loads(result_path.read_text(encoding='utf-8'))
                if result.get('error') or not result.get('thinking_character_count'):
                    summary['error'] = f'Existing result is incomplete at context={profile}, think={level}'
                    failed = True
                    break
                print(f'\n=== Retaining completed context {profile}; effort {level} ===', flush=True)
                summary['results'][profile][level] = result
                continue
            if output.exists():
                summary['error'] = f'Existing incomplete output at context={profile}, think={level}; it was preserved.'
                failed = True
                break
            command = [sys.executable, str(script), '--profiles', profile, '--records', str(records), '--output', str(output),
                       '--pause-tool', str(args.pause_tool), '--work-seconds', '0', '--rest-seconds', '60',
                       '--max-gpu-temp', '95', '--resume-below', '80', '--cooldown-seconds', '0',
                       '--max-seconds', str(args.max_seconds), '--think', level, '--num-predict', str(args.num_predict)]
            print(f'\n=== Context {profile}; thinking effort {level} ===', flush=True)
            process = subprocess.run(command, check=False)
            if process.returncode or not result_path.is_file():
                summary['error'] = f'Benchmark runner failed at context={profile}, think={level} (exit {process.returncode})'
                failed = True
                break
            result = json.loads(result_path.read_text(encoding='utf-8'))
            summary['results'][profile][level] = result
            if result.get('error'):
                summary['error'] = f'Long request failed at context={profile}, think={level}: {result["error"]}'
                failed = True
                break
            if not result.get('thinking_character_count') or result.get('first_thinking_token_sec') is None:
                summary['error'] = f'Ollama returned no thinking output for context={profile}, think={level}; stopping because the requested setting was not confirmed.'
                failed = True
                break
            summary['updated_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
            summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        if failed:
            break
    summary['finished_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(f'\nSummary saved to {summary_path}', flush=True)
    if summary.get('error'):
        print(summary['error'], file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
