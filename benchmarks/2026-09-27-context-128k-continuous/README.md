# 128K continuous context test — 2026-09-27

This run tests the prepared synthetic retrieval prompt on `ser8-qwen38:128k`,
with a requested context of 131,072 tokens. It follows the successful 64K test.

## Result

**Cancelled at the configured 95 C GPU threshold before generation.** The model
loaded at 131,072 context with full reported GPU placement, but the long request
did not complete. No cooling pauses occurred.

| Measurement | Result |
|---|---:|
| Submitted input, server tokenization | 115,451 tokens |
| Last logged processed input | 37,888 tokens / 32.82% |
| Long-request elapsed before cancellation | 826.61 s / 13.78 min |
| First token / generation throughput | Not available |
| Maximum sampled GPU temperature | 95 C |
| Minimum sampled available system RAM | 13.91 GiB |
| Retrieval | Not evaluated; no answer generated |

This attempt establishes successful loading and partial prompt processing, not
successful near-limit retrieval. It does not establish a hardware temperature
limit. The model unloaded after cancellation. The harness's `retrieval: false`
flags mean no matching output was received; they are not evidence of incorrect
retrieval by a completed response.

## Method

- One smoke request followed by one long BEGIN/MIDDLE/END retrieval request.
- Pinned Qwen3.8 27.3B Q4_K_M weights, MTP draft 2, six threads, batch 256,
  f16 KV cache and automatic Flash Attention.
- Seed 42, temperature 0, thinking disabled, output capped at 256 tokens.
- No scheduled rests or process suspension. GPU temperature and whole-system
  available RAM sampled every five seconds.
- GPU was 49 C before launch; no additional initial timed cooldown was requested.
  The harness still requires below 70 C before starting the profile.
- Cancellation threshold: 95 C; request time limit: three hours; available RAM
  below 2 GiB for 30 seconds also cancels. These are test-policy limits, not
  manufacturer temperature ratings. Only the GPU adapter temperature is sampled.

```powershell
python scripts/benchmark-context.py --profiles 128k `
  --output benchmarks/2026-09-27-context-128k-continuous `
  --cooldown-seconds 0 --max-gpu-temp 95 --max-seconds 10800
```

## Evidence

- [Run settings](settings.json) and [machine/server environment](environment.json).
- [Runner arguments](128k/runner.json), with the home directory redacted.
- [Smoke result](128k/smoke-result.json) and [placement](128k/smoke-placement.json).
- [Long request](128k/long-request.json), [streamed response events](128k/long-stream.jsonl)
  and [temperature / available-memory samples](128k/long-memory.json).
- [Result](128k/long-result.json), [interruption summary](128k/interruption.json),
  [selected server log](128k/selected-server-log.txt), [placement at cancellation](128k/long-placement.json)
  and [post-run state](post-run.json).

Available RAM includes background workloads and is not isolated model memory.
This is one synthetic retrieval example, not a general reasoning or code-quality
benchmark. Earlier 32K and 64K runs had different thermal policies and background
workloads, so their timings are not a controlled scaling comparison.
