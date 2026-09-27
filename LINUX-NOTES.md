# Additional Linux setup notes

## Without systemd / undo

For a manually managed installation, with no other server listening:

```bash
env -u OLLAMA_FLASH_ATTENTION -u GGML_VK_VISIBLE_DEVICES \
  OLLAMA_HOST=127.0.0.1:11434 OLLAMA_VULKAN=1 OLLAMA_IGPU_ENABLE=1 \
  OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 \
  OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KV_CACHE_TYPE=f16 \
  OLLAMA_KEEP_ALIVE=15m ollama serve
```

To remove only this service configuration, finish active work and unload its models:

```bash
sudo rm /etc/systemd/system/ollama.service.d/90-ser8.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

If the installer backed up an older version of that file, restore that backup
instead. Models and profiles remain installed.

