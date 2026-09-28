# 64K context test with cooling pauses — 2026-09-27

This run uses one continuous API request. Initially, the matching Windows Ollama
runner was suspended during cooling rests, preserving processed context rather
than cancelling the request and repeating prefill. At the user's request, rests
were disabled partway through and processing continued without cooling breaks.

## Result

**Completed successfully.** All three retrieval codes were correct. The final
API response reported 57,060 input tokens, zero cached input tokens and 256 output
tokens (`done_reason: length`). The full prompt fit within the allocated 65,536
tokens, and no truncation was recorded.

| Measurement | Result |
|---|---:|
| Total request time | 1,813.36 s / 30.22 min |
| Prefill, including early pauses | 1,758.16 s / 29.30 min |
| First token | 1,758.39 s |
| Generation | 4.71 tokens/sec |
| Actual cooling pauses, approximate total | 362.97 s / 6.05 min |
| Full cooling rests | 3 |
| Immediately overridden suspension | 1, approximately 0.78 s |
| Sampled peak GPU temperature | 93 C |
| Minimum sampled available system RAM | 19.23 GiB |

Generation occurred after pauses had been disabled. This run demonstrates one
successful retrieval example under a mixed cooling policy; it does not establish
that sustained 93 C is safe. The model unloaded normally when the request finished.

## Method

- Profile: `ser8-qwen38:64k`, allocated context 65,536 tokens, pinned Q4_K_M
  weights, MTP draft 2, six threads, batch 256, f16 KV, automatic Flash Attention.
- Synthetic BEGIN/MIDDLE/END retrieval prompt, seed 42, temperature 0, thinking
  disabled, output capped at 256 tokens. The saved request contains all input.
- Two-minute rest after at most five minutes of work; rest starts earlier at
  a sampled GPU temperature of 85 C. Sampling interval is five seconds.
- Resume after the rest and only below 70 C. The controller holds a handle to
  the verified runner and targets its PID, preserving the same request.
- Three full rests completed before the user requested continuous processing.
  Because this process predates the `NO_PAUSES` runtime toggle, a separate helper
  resumed subsequent suspensions immediately. Its timestamped
  [override record](64k/continuous-override.json) takes precedence over the
  controller's nominal pause duration for affected events. The helper holds a
  handle to the same PID and never cancels or replaces the request.
- The GPU was already at 40 C following an earlier rest, so this run used no
  additional initial timed cooldown. The request wall-time limit was three hours.
- [Microsoft PsSuspend](https://learn.microsoft.com/en-us/sysinternals/downloads/pssuspend)
  1.09 was obtained from Microsoft and its Authenticode signature verified.
  The executable stays outside the repository. This is an experimental Windows
  benchmark mode; suspending the runner also delays any other requests to it.

These are test-policy temperatures, not hardware maximum ratings. Only the GPU
adapter temperature was monitored. No BIOS, power-limit or fan settings changed.

## Evidence

- [Run settings](settings.json) and [machine/server environment](environment.json).
- [Runner arguments](64k/runner.json), with the home directory redacted.
- [Smoke placement](64k/smoke-placement.json) and [smoke result](64k/smoke-result.json).
- [Long request](64k/long-request.json), [streamed response events](64k/long-stream.jsonl)
  and [sampled temperature / available memory](64k/long-memory.json).
- [Reconciled result](64k/long-result.json), [final API response](64k/long-response.json),
  [answer text](64k/long-response.txt), [final placement](64k/long-placement.json)
  and [selected server log](64k/selected-server-log.txt).
- [Pause and resume events](64k/pauses.json), including timestamps, reason and
  temperatures. PID and timestamps are diagnostic metadata.

The [raw harness result](64k/long-result-raw.json) reports 1,279.63 seconds paused:
its controller remained logically paused after the external helper resumed the
runner. That value overstates the actual suspension. The reconciled result keeps
the original value in `controller_reported_paused_sec`, and substitutes the
override's measured approximate duration for the affected event. All three earlier
rest durations remain unchanged. The sub-second override measurement uses the
pause-state file's modification timestamp, with small process-control overhead
excluded. Model timing, temperature and response measurements are unchanged.

Wall time, first-token latency and API timings include cooling pauses. They
describe this duty cycle and must not be presented as uninterrupted throughput.
Whole-system available memory includes background workloads and is not a direct
measurement of model memory. This is one synthetic retrieval example, not a
general accuracy benchmark.
