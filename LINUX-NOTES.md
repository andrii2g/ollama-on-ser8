# Additional Linux setup notes

## Without systemd

For a manually managed installation, with no other server listening:

```bash
env -u OLLAMA_FLASH_ATTENTION -u GGML_VK_VISIBLE_DEVICES \
  OLLAMA_HOST=127.0.0.1:11434 OLLAMA_VULKAN=1 OLLAMA_IGPU_ENABLE=1 \
  OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
  OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KV_CACHE_TYPE=f16 \
  OLLAMA_KEEP_ALIVE=15m ollama serve
```

Keep that server terminal open. In a second terminal, enter the repository root
and use the local server explicitly:

```bash
export OLLAMA_HOST=127.0.0.1:11434
ollama pull qwen3.8:27b-mtp-q4_K_M
bash scripts/apply-profiles.sh
bash scripts/use-profile.sh 8k
```

The environment assignments on `ollama serve` apply to that process only; they
do not configure other terminals. The helpers always connect to localhost and
do not load a `.env` file. See [the README](README.md#host-configuration) for host
configuration details.

## Undo the systemd configuration

These steps apply only if you installed the systemd drop-in. Finish active work,
then inspect and unload each listed model:

```bash
OLLAMA_HOST=127.0.0.1:11434 ollama ps
# Repeat for each loaded model:
# OLLAMA_HOST=127.0.0.1:11434 ollama stop EXACT_MODEL_NAME
```

Remove the drop-in and restart the service:

```bash
sudo rm /etc/systemd/system/ollama.service.d/90-ser8.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

If the installer backed up an older version of that file, restore that backup
instead. Models and profiles remain installed.

