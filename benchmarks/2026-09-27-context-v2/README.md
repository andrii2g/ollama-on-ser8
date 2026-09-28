# Large-context tests â€” 2026-09-27

Windows 11 SER8, Ryzen 7 8845HS, Radeon 780M, 64 GB installed RAM,
Ollama 0.34.2, Qwen3.8 27.3B Q4_K_M with MTP draft 2. See
[environment.json](environment.json) for the OS build and GPU driver and
[settings.json](settings.json) for run settings and source-weight identity.
These are Windows measurements, not Linux validation.

## Method

One short smoke request loads each profile, followed by one uncached synthetic
retrieval request. The smoke request is not a throughput benchmark. Long requests
contain 760, 1,520 and 3,040 records for 32K, 64K and 128K respectively, with
verification codes at the beginning, middle and end. The answer must return all
three codes and then explain the limits of the synthetic data. The saved request
JSON contains the exact prompt and options. Each request uses thinking off,
seed 42, temperature 0, and a 256-token generation cap for the long case.

The profiles retain six threads, batch 256, MTP draft 2, f16 KV caches and automatic
Flash Attention. Runner snapshots record the effective options. The default
server context stays 8K; each profile/request selects its larger context.
Models are unloaded between sizes. The script refuses to start while another
model is loaded.

## Results

| Profile | Input tokens | Prefill | Generation | Wall time | Retrieval |
|---|---:|---:|---:|---:|---|
| 32K | 28,461 | 831.06 s | 5.32 tok/s | 879.40 s | BEGIN/MIDDLE/END passed |
| 64K | 57,060 in server log | Interrupted | Not reported | Not reported | Not completed |
| 128K | — | Not started in this run | — | — | — |

The 32K row comes from [the saved result](32k/long-result.json) and
[raw response](32k/long-response.json). The 64K run was interrupted at the user's
request for cooling; see [interrupted.json](64k/interrupted.json). Its smoke check
confirmed a 65,536-token allocation and full reported GPU placement, but it has
no complete long response. Remaining tests are rerun with temperature monitoring
and five-minute cooldowns in `../2026-09-27-context-cooled/`.

This original run did not record GPU temperature. A later user-supplied screenshot
showed 74 C; it does not establish the run's peak temperature.

## How to interpret the data

Generation throughput is `eval_count / (eval_duration / 1e9)` and excludes input
processing. Prefill time is `prompt_eval_duration / 1e9`. Time to first token and
wall time are measured by the client; model loading is captured separately in the
smoke request. The long request uses the already loaded model, but the API's
cached-input count is checked separately.

Available RAM is sampled for the entire Windows system every five seconds. It is
not model-only memory, and its minimum can miss a short peak. Other processes and
Windows memory reclamation affect it; the machine is not an isolated laboratory
system. `size_vram` on this integrated GPU refers to shared memory, not separate
dedicated VRAM, and the placement snapshot is not a complete system RAM accounting.

Passing the three synthetic retrieval checks does not establish general reasoning
accuracy across the context. The 256-token cap can cut off the explanatory prose.
These are single runs, without confidence intervals. A profile's configured
capacity and its tested input length are reported separately; no run tests a
completely full context, because output requires headroom.

An [initial oversized 32K attempt](../2026-09-27-context/README.md) was cancelled
after Ollama logged input truncation. It is excluded from successful results.
The revised run checks that actual input counts are near the intended capacity
and that all three verification codes survive. Inspect the saved responses and
logs if repeating with different prompts or runtime versions.

## Reproduce

From the repository root, on an idle local Ollama server:

```bash
bash scripts/apply-profiles.sh 32k 64k 128k
python3 scripts/benchmark-context.py --output benchmarks/my-context-run
```

On Windows, create the same Modelfiles with `ollama create` and run the Python
harness with `python`. The source model must already be downloaded and match the
pinned weights. The harness does not configure or restart the server. It limits
each long request to 90 minutes and cancels on available RAM below 2 GiB for
30 seconds. Choose a new output directory to preserve previous evidence.
