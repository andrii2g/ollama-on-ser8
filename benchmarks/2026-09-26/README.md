# SER8 benchmark evidence — 2026-09-26

These are saved Windows test results, reviewed on 2026-09-27. The reported
machine was a Beelink SER8 with Ryzen 7 8845HS, Radeon 780M and 64 GB
(2 × 32 GB DDR5-5600), running Windows 11. Ollama settings record version 0.34.2.
The files do not provide a complete OS-build, driver, BIOS or power-limit inventory.
They do not validate the Linux setup scripts.

## What the measurements support

- MTP draft 2 improved generation throughput over draft 0 on all three
  512-token tasks. Those responses all ended at the token limit.
- Batch 128 and 256 were close. Batch 512 and 1024 did not improve the
  dedicated batch sweep. These are individual observations, not a statistical
  proof that 256 is optimal.
- The 16K configuration processed 8,583 input tokens; it was not tested with
  a full 16K input. Long-input prefill remained a substantial part of latency.
- The specific Q4_K_M model outperformed the specific IQ4_XS model on every
  compared workload. This is not a general ranking of quantization formats.
- Small synthetic retrieval and fact-extraction checks were recorded as passing.
  Generated C# was not established as correct by these timing measurements.

## Model and execution settings

Most Ollama runs used six threads, batch 256, draft 2, and an 8,192-token
context; the sweeps changed the named parameter. The saved throughput/context
settings record temperature 0, seed 42 and thinking disabled. Runtime comparisons
used explicit ChatML prompts with a closed thinking block and raw completion APIs.
Consult each suite's settings rather than assuming identical request formats.

Historical files name `qwen3.8:latest`. The runtime settings record that tag's
manifest as `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`,
matching this repository's pinned source check. The model blob recorded there is
`f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d`.
Use the explicit `qwen3.8:27b-mtp-q4_K_M` tag and digest check from the setup guide;
today's `latest` tag should not be assumed to identify the historical model.

The [configuration snapshot](SER8-config-20260926-223340-038/configuration.json)
records both saved profiles. The [8K smoke response](SER8-config-20260926-223340-038/smoke-response.json)
completed normally, and its [placement snapshot](SER8-config-20260926-223340-038/smoke-placement.json)
reports context 8192 with `size_vram == size`. The
[runner command](SER8-config-20260926-223340-038/smoke-runners.json)
records `draft-mtp`, draft length 2, f16 caches, automatic Flash Attention,
batch/ubatch 256, and six threads. Reported GPU placement alone does not prove
which GPU backend was used, and the 780M uses shared system RAM.

## Saved measurements

The tables below transcribe the original CSV values. Generation throughput is
output tokens divided by generation duration; it excludes prefill and loading.
Ollama JSON durations are in nanoseconds. `WallSec` is the original harness's
elapsed-time measurement and can exceed the server-reported total duration.

### Batch 256 / 512 / 1024

Source: [SER8-batch-20260926-194205-433](SER8-batch-20260926-194205-433/measurements.csv); [settings](SER8-batch-20260926-194205-433/settings.json).

| Batch | Context | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 256 | 8192 | 3395 | 0 | 256 | 6.536 | 56.94 | 96.44 |
| 512 | 8192 | 3395 | 0 | 256 | 6.462 | 58.56 | 98.57 |
| 1024 | 8192 | 3395 | 0 | 256 | 6.282 | 61.52 | 102.61 |

### Context sizes

Source: [SER8-context-20260926-191434-228](SER8-context-20260926-191434-228/measurements.csv); [settings](SER8-context-20260926-191434-228/settings.json).

| Context | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- |
| 8192 | 3395 | 0 | 256 | 6.528 | 57.07 | 96.65 |
| 16384 | 8583 | 0 | 256 | 6.463 | 149.46 | 189.45 |

### Quantization comparison

Source: [SER8-quants-20260926-221535-911](SER8-quants-20260926-221535-911/measurements.csv); [settings](SER8-quants-20260926-221535-911/settings.json).

| Quant | Case | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q4_K_M | SQL | 53 | 0 | 128 | 7.267 | 1.88 | 20.03 |
| Q4_K_M | SQL | 53 | 49 | 128 | 7.544 | 0.47 | 17.88 |
| Q4_K_M | Context100 | 3395 | 0 | 256 | 6.63 | 73.55 | 112.48 |
| IQ4_XS | SQL | 53 | 0 | 128 | 5.857 | 2.27 | 24.51 |
| IQ4_XS | SQL | 53 | 49 | 128 | 5.415 | 0.49 | 24.55 |
| IQ4_XS | Context100 | 3395 | 0 | 256 | 5.171 | 73 | 122.89 |
| IQ4_XS | CSharp | 178 | 0 | 343 | 6.719 | 4.42 | 56.47 |
| IQ4_XS | Facts | 195 | 0 | 78 | 7.047 | 4.4 | 16.01 |
| Q4_K_M | CSharp | 178 | 0 | 372 | 8.231 | 4.34 | 49.99 |
| Q4_K_M | Facts | 195 | 0 | 78 | 8.649 | 4.35 | 13.85 |

### MTP comparison

Source: [SER8-results-20260926-184042-475](SER8-results-20260926-184042-475/measurements.csv); [settings](SER8-results-20260926-184042-475/settings.json).

| Case | Draft | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SQL | 0 | 53 | 0 | 512 | 4.096 | 2.28 | 128.51 |
| SQL | 2 | 53 | 0 | 512 | 7.158 | 1.44 | 73.35 |
| CSharp | 2 | 119 | 0 | 512 | 8.11 | 2.52 | 66.07 |
| CSharp | 0 | 119 | 0 | 512 | 4.087 | 3.38 | 129.91 |
| Summary | 0 | 416 | 0 | 512 | 3.773 | 9.38 | 146.29 |
| Summary | 2 | 416 | 0 | 512 | 7.753 | 7.81 | 74.24 |

### Runtime comparison

Source: [SER8-runtime-20260926-210224-568](SER8-runtime-20260926-210224-568/measurements.csv); [settings](SER8-runtime-20260926-210224-568/settings.json).

| Runtime | Case | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ollama | SQL | 53 | 0 | 128 | 7.524 | 1.49 | 18.9 |
| Ollama | Context100 | 3395 | 0 | 256 | 6.501 | 61.25 | 101.07 |
| LlamaCpp | SQL | 53 | 180 | 128 | 7.368 | 1.71 | 19.44 |
| LlamaCpp | Context100 | 3395 | 3650 | 256 | 6.382 | 46.34 | 86.86 |

### Runtime comparison

Source: [SER8-runtime-20260926-212637-375](SER8-runtime-20260926-212637-375/measurements.csv); [settings](SER8-runtime-20260926-212637-375/settings.json).

| Runtime | Case | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ollama | SQL | 53 | 0 | 128 | 7.497 | 1.56 | 19.06 |
| Ollama | Context100 | 3395 | 0 | 256 | 6.444 | 62.7 | 102.86 |
| LlamaCpp | SQL | 53 | 180 | 128 | 7.233 | 1.36 | 19.46 |
| LlamaCpp | Context100 | 3395 | 3650 | 256 | 6.370 | 46.62 | 87.23 |

### 16K runtime comparison

Source: [SER8-runtime16K-20260926-213813-835](SER8-runtime16K-20260926-213813-835/measurements.csv); [settings](SER8-runtime16K-20260926-213813-835/settings.json).

| Runtime | Case | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LlamaCpp | SQL | 53 | 0 | 128 | 7.327 | 1.35 | 19.21 |
| LlamaCpp | Context260 | 8583 | 0 | 256 | 5.938 | 120.89 | 164.43 |
| Ollama | SQL | 53 | 0 | 128 | 7.113 | 1.56 | 20 |
| Ollama | Context260 | 8583 | 0 | 256 | 6.524 | 156.26 | 195.97 |

### Batch 64 / 128 / 256

Source: [SER8-small-batch-20260926-201021-902](SER8-small-batch-20260926-201021-902/measurements.csv); [settings](SER8-small-batch-20260926-201021-902/settings.json).

| Batch | Context | PromptTokens | CachedTokens | OutputTokens | GenTokPerSec | PrefillSec | WallSec |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 128 | 8192 | 3395 | 0 | 256 | 6.529 | 56.36 | 95.95 |
| 64 | 8192 | 3395 | 0 | 256 | 6.353 | 56.17 | 96.85 |
| 256 | 8192 | 3395 | 0 | 256 | 6.486 | 58.84 | 98.75 |

## Interpretation and limitations

There are 36 measured CSV rows across eight suites, plus a separate configuration
smoke check. Most configurations have one measured run per case. Two 8K runtime
comparison folders are separate recorded runs, not averaged results. The
quantization SQL rows include repeated prompts: the second SQL run for each
quantization reports 49 cached tokens. Keep cold and cached observations separate.

The llama.cpp comparisons used the Windows Vulkan b11200 prerelease. In both 8K
comparisons its CSV reports cached-token values unlike Ollama's, including values
larger than `PromptTokens`. These fields are not a demonstrated common measure
of reused input across the two runtimes; do not infer an uncached prefill advantage
from those rows. The 16K comparison records zero cached tokens for both runtimes,
but still contains only one run per case. No general runtime winner is established.

The archived context/batch checks report BEGIN/MIDDLE/END retrieval passes, and
the quantization suite reports retrieval/fact passes. These are the original
harness's recorded flags, not newly rerun tests or a broad accuracy assessment.
Many outputs hit their token limit. Neither speed nor a retrieval flag proves
that a generated program is correct.

The earlier README mentioned a CPU-only baseline and a sweep of draft lengths
1, 3 and 4. Supporting measurements for those claims were not found in the
reviewed folders, so they are not used in the current benchmark summary.
The Linux mocked API/CLI tests are also not supplied by these Windows artifacts.

## Evidence contents and replay

The source directory names are preserved. This archive includes the original
measurement CSVs, suite settings, prompt text where available, and saved response
JSON. The MTP comparison embeds its prompts inside `settings.json`. JSON files
were reformatted, and the local Windows user-directory prefix was replaced with
`%USERPROFILE%`; measurements and response contents were otherwise preserved.
Model binaries, runtime installations, full runtime logs, redundant response text
exports and large model metadata dumps are not included.

The original benchmark execution harness was not found in these folders. The
archive supports auditing the recorded metrics and reconstructing experiments,
but is not a one-command replay suite. To repeat a case, use its saved prompt,
model identity and settings; match the API/prompt format, output cap and cache
conditions; save the request and response; record driver/OS versions and runtime
placement; and repeat measurements before drawing conclusions about small gaps.
Compare each run's token counts and stopping reason as well as throughput.
