#!/usr/bin/env bash
# Start a fresh CLI conversation; finish other clients' requests before switching.
set -euo pipefail
export OLLAMA_HOST=127.0.0.1:11434
case "${1:-}" in
    8k) model=ser8-qwen38:8k; other=ser8-qwen38:16k ;;
    16k) model=ser8-qwen38:16k; other=ser8-qwen38:8k ;;
    *) echo 'Usage: bash scripts/use-profile.sh {8k|16k}' >&2; exit 2 ;;
esac
command -v ollama >/dev/null
# Fail before unloading if the target is missing or these client flags are unsupported.
ollama show "$model" >/dev/null
help_text=$(ollama run --help)
if [[ $help_text != *--think* || $help_text != *--keepalive* ]]; then
    echo 'This CLI lacks the required --think/--keepalive flags. Use the tested Ollama version.' >&2
    exit 1
fi
if ollama show "$other" >/dev/null 2>&1; then
    ollama stop "$other"
fi
echo "Starting $model; thinking off, keep-alive 15 minutes. Type /bye to exit."
exec ollama run "$model" --think=false --keepalive 15m
