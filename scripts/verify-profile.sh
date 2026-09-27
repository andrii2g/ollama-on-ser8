#!/usr/bin/env bash
# Checks the live placement AFTER a request; it does not load or switch a model.
set -euo pipefail
case "${1:-}" in 8k|16k) ;; *) echo 'Usage: bash scripts/verify-profile.sh {8k|16k}' >&2; exit 2 ;; esac
python3 - "$1" <<'PY'
import json, sys, urllib.request
model = 'ser8-qwen38:' + sys.argv[1]
context = {'8k':8192,'16k':16384}[sys.argv[1]]
http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with http.open('http://127.0.0.1:11434/api/ps', timeout=15) as r:
        models = json.load(r)['models']
    match = next((m for m in models if m['name'] == model), None)
    if match is None:
        raise RuntimeError('Profile is not loaded. Send a message with it first.')
    print(json.dumps({k:match.get(k) for k in ('name','context_length','size','size_vram')}, indent=2))
    if match.get('context_length') != context:
        raise RuntimeError('Context mismatch: check client overrides.')
    if match.get('size',0) <= 0 or match.get('size_vram',0) < 0.99*match['size']:
        raise RuntimeError('Full reported GPU placement was not obtained; check Vulkan driver/service access and logs.')
    if len(models) != 1:
        raise RuntimeError('More than one model is loaded; check server/client concurrency.')
    print('Context and full reported GPU placement passed. Radeon 780M GPU memory is shared system RAM.')
    print('Also inspect server logs for Vulkan and MTP draft length 2; placement alone cannot prove either.')
except (OSError, ValueError, RuntimeError) as exc:
    print('ERROR:', exc, file=sys.stderr)
    sys.exit(1)
PY
