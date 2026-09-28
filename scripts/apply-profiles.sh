#!/usr/bin/env bash
# Creates selected profiles (8k and 16k by default) from verified, already-downloaded weights. No implicit pull.
set -euo pipefail
export OLLAMA_HOST=127.0.0.1:11434
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
command -v ollama >/dev/null
command -v python3 >/dev/null
python3 - "$root" "$@" <<'PY'
import json, pathlib, re, subprocess, sys, urllib.error, urllib.request

BASE = 'http://127.0.0.1:11434'
DIGEST = '22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643'
WEIGHT = 'f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d'
SOURCE = 'qwen3.8:27b-mtp-q4_K_M'
ROOT = pathlib.Path(sys.argv[1])
CONTEXTS = {'8k':8192, '16k':16384, '32k':32768, '64k':65536, '128k':131072}
selected = sys.argv[2:] or ['8k', '16k']
if any(tag not in CONTEXTS for tag in selected):
    sys.exit('Usage: bash scripts/apply-profiles.sh [8k|16k|32k|64k|128k ...]')
http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def api(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, headers={'Content-Type':'application/json'})
    with http.open(request, timeout=60) as response:
        return json.load(response)

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

try:
    version = api('/api/version')['version']
    print('Server:', version)
    if version != '0.34.2':
        print('NOTE: benchmark version was 0.34.2. Verify placement and MTP on this version.')
    models = {m['name']:m for m in api('/api/tags')['models']}
    require(SOURCE in models, f'Missing source. Run: ollama pull {SOURCE}')
    require(models[SOURCE]['digest'] == DIGEST,
            'Source tag differs from the tested manifest. No profiles changed. Review this model revision first.')
    info = api('/api/show', {'model':SOURCE})
    require(info['details']['quantization_level'] == 'Q4_K_M', 'Unexpected source quantization.')
    require(WEIGHT in info.get('modelfile',''), 'Unexpected source weights.')
    require(info.get('model_info',{}).get('qwen35.nextn_predict_layers',0) >= 1,
            'Source does not report the expected MTP layer.')
    # Check selected targets before mutating any profile.
    for tag in selected:
        target = 'ser8-qwen38:' + tag
        if target in models:
            old = api('/api/show', {'model':target})
            require(WEIGHT in old.get('modelfile',''), f'{target} exists with other weights; not replaced.')
    for tag in selected:
        context = CONTEXTS[tag]
        target = 'ser8-qwen38:' + tag
        subprocess.run(['ollama','create',target,'-f',str(ROOT/'profiles'/('Modelfile.'+tag))], check=True)
        result = api('/api/show', {'model':target})
        require(WEIGHT in result.get('modelfile',''), 'Created profile has unexpected weights.')
        expected = dict(num_ctx=context,num_thread=6,num_batch=256,draft_num_predict=2,temperature=0)
        for name,value in expected.items():
            pattern = rf'(?m)^{re.escape(name)}\s+{value}(?:\.0+)?\s*$'
            require(re.search(pattern,result.get('parameters','')), f'{target}: {name} verification failed.')
        print('Verified:', target)
    print('Profiles saved. Run: bash scripts/use-profile.sh PROFILE')
except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
    print('ERROR:', exc, file=sys.stderr)
    sys.exit(1)
PY
