# SER8 32K / 64K / 128K context tests — 2026-09-27

**32K, 64K and 128K completed the synthetic retrieval test.** Earlier 128K attempts
stopped at their chosen GPU temperature limits; the final retry succeeded.
The completed 64K request initially used cooling pauses; at the user's request,
further rests were disabled and it continued to completion. These Windows results
do not establish Linux performance or a hardware maximum temperature.

## Results

| Profile | Allocated context | Long prompt tokens | Outcome | Long-request elapsed | Sampled GPU peak |
|---|---:|---:|---|---:|---:|
| 32K | 32,768 | 28,461 | Completed; all three retrieval codes correct | 879.40 s (14.66 min) | Not recorded |
| 64K, mixed cooling policy | 65,536 | 57,060 | Completed; all three retrieval codes correct | 1,813.36 s (30.22 min), includes early rests | 93 C |
| 128K, thermal-pause mode | 131,072 | 115,451 | Completed; all three retrieval codes correct; no pauses triggered | 3,887.23 s (64.79 min) | 93 C |
| 64K, cooled retry | 65,536 | 57,060 | Cancelled during prefill by temperature guard | 210.50 s | 86 C |
| 128K, continuous retry | 131,072 | 115,451 | Cancelled at ~33% prefill by temperature guard; no answer | 826.61 s (13.78 min) | 95 C |
| 128K, cooled attempt | 131,072 | 115,451 | Cancelled during prefill by temperature guard | 210.50 s | 85 C |

The completed 32K, 64K and 128K token counts come from final API responses. For cancelled requests,
token counts come from server prompt-tokenization logs and describe submitted
input, not fully processed input. All three allocations showed full reported
GPU placement on the shared-memory Radeon 780M. That status is not a complete
accounting of system RAM use.

For the completed 32K request, prefill took **831.06 seconds (13.85 minutes)**,
first token arrived after **831.21 seconds**, and generation averaged
**5.32 tokens/sec** for 256 output tokens. The cached-input count was zero.
The answer hit its token limit after returning all three codes. This establishes
only the small synthetic retrieval check, not broad reasoning or code quality.

The completed 64K request had **1,758.16 seconds (29.30 minutes) of prefill**,
including approximately **362.97 seconds of pauses**, and a first token at
1,758.39 seconds. Generation averaged **4.71 tokens/sec** for 256 output tokens;
all cooling pauses occurred during prefill. Cached-input count was zero and all
three codes were correct. The answer then hit the output cap. Context allocation
was 65,536 and input plus output remained within it; no truncation was recorded.
Minimum sampled available RAM was 19.23 GiB. The run finished normally and the
model unloaded afterward.

The earlier **128K continuous retry** had no cooling pauses and a 95 C cancellation
threshold. It stopped after **826.61 seconds (13.78 minutes)** with 37,888 of
115,451 submitted tokens processed in the last server progress entry (32.82%).
No first token or final API response was produced, so that attempt did not measure
retrieval or generation throughput. Minimum sampled available RAM was **13.91 GiB**;
the cancellation was triggered by temperature, not the memory guard. The model
unloaded normally afterward.

The **successful 128K retry** configured a one-minute minimum pause at 95 C,
resuming below 80 C, with no scheduled rests. Peak sampled temperature was 93 C,
so **zero pauses occurred**. It processed all 115,451 input tokens with zero cached
input and generated 256 output tokens, including all three correct retrieval codes.
Prefill took **3,818.61 seconds (63.64 minutes)**, the first token arrived after
3,818.93 seconds, and generation averaged **3.75 tokens/sec**. Total request time
was **3,887.23 seconds (64.79 minutes)**. Minimum available RAM was 14.06 GiB.
Input plus output remained within the 131,072-token allocation, no truncation was
recorded, and the model unloaded normally. The answer reached its output cap.

The 32K run was completed before temperature sampling was added, so it cannot
be described as having passed the later 85 C policy. Minimum sampled available
system RAM was 5.02 GiB during 32K, 20.86 GiB during the cooled 64K attempt and
16.52 GiB during the first 128K attempt. Background workload and memory reclamation changed over
the session; these values are not isolated model-memory comparisons.

## Evidence and excluded attempts

- [32K result and original 64K interruption](2026-09-27-context-v2/README.md).
  The first 64K run processed 57,060 input tokens and began generation, but the
  user requested a cooling break before a final response was saved. It is not
  counted as a completed benchmark.
- [Completed 64K request](2026-09-27-context-64k-paused/README.md), with early
  cooling pauses, the later continuous-processing override, final response and
  reconciled pause accounting.
- [64K cooled retry](2026-09-27-context-cooled/README.md), including temperatures,
  request, placement and interruption evidence.
- [128K cooled attempt](2026-09-27-context-128k-cooled/README.md), with the same
  evidence categories.
- [128K continuous retry](2026-09-27-context-128k-continuous/README.md), including
  the 95 C interruption, partial prefill progress and post-run cleanup.
- [Completed 128K retry](2026-09-27-context-128k-paused/README.md), with thermal
  pauses enabled but none triggered, complete response and final metrics.
- [Excluded oversized 32K attempt](2026-09-27-context/README.md). Its 33,701-token
  prompt exceeded context and was truncated; it was cancelled and resized.

Hardware: Windows 11 SER8, Ryzen 7 8845HS, Radeon 780M, 64 GB installed RAM;
Ollama 0.34.2 and the pinned Qwen3.8 27.3B Q4_K_M weights. All profiles use MTP
draft 2, six threads, batch 256, f16 cache and automatic Flash Attention.
The long requests use seed 42, temperature 0, thinking disabled and a 256-token
output cap. There is one completed run at each context size. Different cooling
policies and background workloads prevent a controlled throughput comparison;
no statistical confidence interval or repeatability claim is available.

## Cooldown policy and practical interpretation

The guarded retries rested for **at least five minutes before each profile** and
required a temperature **below 70 C** before starting. They sampled GPU temperature
every five seconds, cancelling at **85 C or above**, then unloading the model.
A sample can exceed the threshold between reads, as the 86 C reading illustrates.
The thresholds are user-selected test policy, not manufacturer limits. The sensor
is the Windows adapter temperature; CPU temperature was not monitored.

Those original breaks occurred between profiles. Cancelling a request is not a
resumable pause; its prefill must be repeated for a fresh uncached benchmark.
The later 64K run used Microsoft PsSuspend to preserve the runner and request
during rests: two minutes after at most five minutes of work, or earlier at 85 C.
Three full rests completed before the user requested no further pauses. A fourth
suspension was resumed immediately (approximately 0.78 seconds), and processing
continued to completion with a sampled peak of 93 C. This mixed policy neither
passed the original 85 C cutoff nor tested uninterrupted execution from start to
finish. The unsuccessful continuous 128K retry started with the GPU at 49 C and used no pauses;
its configured 95 C threshold stopped prefill before a response was generated.
The successful retry started at 38 C with a resumable pause controller, but stayed
below its 95 C trigger for the entire request. These observations do not identify
the cause of the temperature difference or validate sustained operation at 93 C.
This benchmark harness did not change BIOS, power limits or fan settings.

Keep 8K/16K for routine use. The opt-in 32K profile has a completed near-limit
example but substantial first-token latency. The 64K profile now also has a
completed example, with long latency and the cooling-policy qualification above.
The 128K profile also passed its near-limit example, but required over an hour
before the first token. Keep the larger profiles opt-in and experimental.
The harness retains a default 90-minute request limit and low-RAM guard; the
completed 64K run and unsuccessful continuous 128K retry allowed three hours,
and the successful 128K retry allowed four hours.

## Run again

```bash
bash scripts/apply-profiles.sh 32k 64k 128k
python3 scripts/benchmark-context.py --profiles 64k 128k --output benchmarks/new-cooled-run
```

The current harness implements the cooldown and temperature limits, saves streamed
responses incrementally, and accepts a `STOP` file in the output directory for
cancellation. Use a new output directory. The source model and a local server
must already be installed; the harness does not configure the server. The
[profile and guard tests](../tests/) run without starting a GPU workload.

For optional in-request pauses and the `NO_PAUSES` runtime toggle, see the
[benchmark instructions](../BENCHMARKING.md). The completed 64K evidence
records its actual command settings and the mid-run override separately.
