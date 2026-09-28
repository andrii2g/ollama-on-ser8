# 128K context test with temperature-triggered pauses — 2026-09-27

This retry preserves the same long API request when the GPU reaches 95 C.
It uses the prepared synthetic BEGIN/MIDDLE/END retrieval prompt and the
`ser8-qwen38:128k` profile with 131,072 allocated context tokens.

## Result

**Completed successfully: all three retrieval codes were correct.** The final
API response reports 115,451 input tokens, zero cached input tokens and 256 output
tokens. Input plus output fit within the context budget; the server recorded
`truncated = 0`. The answer returned all codes before reaching its output cap
(`done_reason: length`).

| Measurement | Result |
|---|---:|
| Total request time | 3,887.23 s / 64.79 min |
| Prefill | 3,818.61 s / 63.64 min |
| First token | 3,818.93 s / 63.65 min |
| Generation | 3.75 tokens/sec |
| Peak sampled GPU temperature | 93 C |
| Minimum sampled available system RAM | 14.06 GiB |
| Actual pauses / paused time | 0 / 0 s |

The pause controller was enabled, but the sampled temperature never reached
95 C, so this request ran continuously. The output directory name describes the
configured mode, not an observed pause. Likewise, `timings_include_cooling_pauses`
is true because pause mode was enabled, but `pause_count` and `paused_sec` are zero.
The model unloaded normally after completion. This single run does not explain
why the earlier continuous retry reached 95 C or establish a safe sustained
temperature or repeatable thermal behavior.

## Method

- Pinned Qwen3.8 27.3B Q4_K_M weights, MTP draft 2, six threads, batch 256,
  f16 KV cache and automatic Flash Attention.
- One smoke request, then one long request: seed 42, temperature 0, thinking
  disabled and 256 output tokens maximum.
- No scheduled pauses. At a sampled GPU temperature of 95 C or above, suspend
  only the verified benchmark runner using Microsoft PsSuspend. Retain the
  process, GPU allocation and processed context, and keep the API request open.
- Rest at least 60 seconds, then resume once the GPU is below 80 C. Sample GPU
  adapter temperature and whole-system available RAM every five seconds.
- Started with the GPU at 38 C; no additional initial timed cooldown. A four-hour
  request limit and the guard for available RAM below 2 GiB for 30 seconds remain.
- Temperature thresholds are user-selected test policy, not hardware ratings.
  The harness does not change BIOS, fan settings or power limits.

```powershell
python scripts/benchmark-context.py --profiles 128k `
  --output benchmarks/2026-09-27-context-128k-paused `
  --pause-tool C:\Tools\PsTools\pssuspend64.exe `
  --work-seconds 0 --rest-seconds 60 --max-gpu-temp 95 --resume-below 80 `
  --cooldown-seconds 0 --max-seconds 14400
```

The actual tool was a Microsoft-signed PsSuspend 1.09 executable in a temporary
directory outside the repository. Replace the example path with your local path.

## Evidence

- [Settings](settings.json) and [machine/server environment](environment.json).
- [Runner arguments](128k/runner.json), with the home directory redacted.
- [Smoke result](128k/smoke-result.json) and [placement](128k/smoke-placement.json).
- [Long request](128k/long-request.json), [streamed response events](128k/long-stream.jsonl)
  and [temperature / available-memory samples](128k/long-memory.json).
- [Pause and resume events](128k/pauses.json).
- [Final result](128k/long-result.json), [API response](128k/long-response.json),
  [answer text](128k/long-response.txt), [final placement](128k/long-placement.json),
  [selected server log](128k/selected-server-log.txt) and [post-run state](post-run.json).

Elapsed and API timings would include any pauses; none occurred. Available RAM reflects background
workloads as well as the model. A single synthetic retrieval example does not
establish general long-context accuracy, and the different thermal policies of
the 32K/64K/128K runs prevent a controlled throughput comparison.
