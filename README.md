# Qwen3.8 on a SER8 with 64 GB RAM

Recommended starting configuration for a Beelink SER8 with **Ryzen 7 8845HS,
Radeon 780M and 2 x 32 GB DDR5-5600**: Ollama, **27.3B Q4_K_M weights with MTP**,
Vulkan acceleration, two everyday context profiles, and three opt-in large-context profiles.

**Evidence:** Windows benchmark artifacts from 2026-09-26 are included in
[the benchmark report](benchmarks/2026-09-26/README.md): measurements, settings,
prompts and saved API responses from Ollama 0.34.2. The test machine was the
Windows 11 SER8 described above. The [2026-09-27 context tests](benchmarks/2026-09-27-context-results.md)
add completed 32K, 64K and 128K results, with earlier temperature-limited attempts preserved.
The Linux setup below is an adaptation, not a measured Linux performance claim.
Linux drivers, backend builds, power limits and available RAM can change results.
This guide targets native Linux; WSL and Docker GPU setup are outside its scope.

## Reported benchmark configuration

| Setting | Recommendation |
|---|---|
| Model | `qwen3.8:27b-mtp-q4_K_M` |
| GPU backend | Vulkan, with full reported GPU placement |
| MTP draft tokens | 2 |
| CPU threads / batch | 6 / 256 |
| KV cache / Flash Attention | f16 / automatic |
| Concurrent requests / loaded models | 1 / 1 |
| Thinking / keep-alive | Off for benchmark-like latency / 15 minutes |

On three 512-token tasks, MTP draft 2 generated at **7.16-8.11 tokens/sec**,
compared with **3.77-4.10** with draft 0. These runs hit their output-token limits;
they measure throughput, not completed-task quality. Long-context Ollama runs
were around **6.5 tokens/sec**. Batch 128 and 256 were close in the saved runs;
larger batches offered no improvement. The tested IQ4_XS file generated slower
than Q4_K_M in every compared workload.

Long input still costs time: the dedicated context test took **57.07 seconds**
for 3,395 uncached input tokens and **149.46 seconds** for 8,583. A separate 16K
runtime comparison recorded **156.26 seconds** for the latter input. The 16K
profile was tested with 8,583 input tokens, not a full 16K input. Small retrieval
checks passed; these are not general accuracy or code-correctness benchmarks.
See the [report and source data](benchmarks/2026-09-26/README.md) for per-case
results, cache differences, and limits on these comparisons.

## The profiles

| Profile | Context budget | Use |
|---|---:|---|
| `ser8-qwen38:8k` | 8,192 tokens | Default: chat and coding |
| `ser8-qwen38:16k` | 16,384 tokens | Longer documents and conversations |
| `ser8-qwen38:32k` | 32,768 tokens | Experimental: large documents |
| `ser8-qwen38:64k` | 65,536 tokens | Experimental: extended context |
| `ser8-qwen38:128k` | 131,072 tokens | Experimental: very large context |

All profiles use `num_thread=6`, `num_batch=256`, `draft_num_predict=2` and
`temperature=0`. Temperature 0 matches the benchmarks; it is a sampling choice,
not a universal quality recommendation. Context includes input, history and output.
Profiles inherit the source template and projector and reuse the same model blobs.

## Linux setup

Requirements: Git (for cloning), Bash, Python 3, Ollama with Vulkan and this model's MTP support,
and a working AMD Vulkan driver. Install Ollama using the [official Linux
instructions](https://docs.ollama.com/linux); 0.34.2 is the benchmark reference.
The standard `ollama.service` is assumed below.

Check GPU access using `vulkaninfo --summary` (install your distribution's Vulkan
tools if needed). The GPU must also be accessible to the service account. Ollama's
[hardware guide](https://docs.ollama.com/gpu) notes that the service user may need
membership in `render`. Check `ls -l /dev/dri/` and the service's user before
changing permissions; do not run the daemon as root to work around GPU access.

Run these commands on the Linux SER8. Clone the repository and enter its root:

```bash
git clone https://github.com/andrii2g/ollama-on-ser8.git
cd ollama-on-ser8
```

If you already downloaded or cloned the project, open its root directory instead.
Run all following commands from that directory.

### Host configuration

The supplied scripts connect only to `127.0.0.1:11434`. The profile creation and
chat helpers override an inherited `OLLAMA_HOST`; the Python API checks also use
that fixed address. There is currently no `.env` loading or remote-host support
in these helpers.

For CLI commands, `OLLAMA_HOST` selects the server to connect to. In the systemd
drop-in and `ollama serve` command, it sets the server's listening address. This
setup uses localhost for both. Set the client host explicitly so downloads and
checks reach the same server as the helpers:

```bash
export OLLAMA_HOST=127.0.0.1:11434
```

This export applies only to the current shell; repeat it in new terminals, or
use the inline assignments shown below. Local graphical/API clients should
connect to `http://127.0.0.1:11434`.

### Install the service configuration and profiles

```bash
# Install a persistent systemd drop-in. Uses sudo where needed.
bash scripts/configure-server.sh

# Finish any running work; stop each loaded model shown by ollama ps.
ollama ps
# ollama stop EXACT_MODEL_NAME
sudo systemctl restart ollama

# Download once (or reuse the already-downloaded explicit tag).
ollama pull qwen3.8:27b-mtp-q4_K_M

# Create and verify both profiles. Run as your normal user.
bash scripts/apply-profiles.sh
```

The service drop-in enables Vulkan/iGPU use, one parallel request, one loaded
model, an 8K default context, f16 KV cache and a 15-minute keep-alive. It leaves
Flash Attention and device selection automatic. Other service overrides can
conflict: inspect `systemctl cat ollama` if placement differs. The 16K model's
saved `num_ctx` overrides the server's 8K default unless a client overrides it.

The installer backs up its own existing drop-in and does not restart the daemon
automatically. Profile creation verifies the exact tested source manifest:

```text
22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643
```

If the tag changes, creation stops before changing profiles. Do not substitute
`latest` or remove the check without reviewing and testing the new weights.

## Optional large-context profiles

The default installer still creates only 8K and 16K. Create the larger profiles
explicitly after downloading and verifying the source model:

```bash
bash scripts/apply-profiles.sh 32k 64k 128k
bash scripts/use-profile.sh 32k   # or 64k / 128k
```

After sending a message, check the allocated context and placement in another
terminal:

```bash
bash scripts/verify-profile.sh 32k   # match the profile you used
```

These profiles reuse the model weights; they increase runtime memory requirements.
Context includes the prompt, conversation history, and generated output. A model
loading successfully does not establish that near-limit prompts are fast or that
all input is retained. Keep output headroom and check server logs for truncation.

### Large-context results (Windows, 2026-09-27)

**32K, 64K and 128K completed the long-context retrieval test successfully.**
Separate profiles were created and their requested context allocations verified.
All three runs used the pinned Qwen3.8 27.3B Q4_K_M model with MTP draft 2, six threads,
batch 256, f16 KV cache and automatic Flash Attention on the Radeon 780M.

| Measurement | 32K | 64K | 128K |
|---|---:|---:|---:|
| Allocated context | 32,768 tokens | 65,536 tokens | 131,072 tokens |
| Input processed | 28,461 tokens | 57,060 tokens | 115,451 tokens |
| Cached input | 0 tokens | 0 tokens | 0 tokens |
| Beginning / middle / end retrieval | All 3 correct | All 3 correct | All 3 correct |
| Generated output | 256 tokens | 256 tokens | 256 tokens |
| Prompt processing (prefill) | 13.85 min | 29.30 min, including cooling rests | 63.64 min |
| Total request time | 14.66 min | 30.22 min, including cooling rests | 64.79 min |
| Generation speed | 5.32 tokens/sec | 4.71 tokens/sec | 3.75 tokens/sec |
| Sampled peak GPU temperature | Not recorded | 93 C | 93 C |

The prompts used about 87–88% of the allocated context. Input plus output stayed
within the context budget; none of the completed runs truncated its input. All answers
returned all three verification codes before reaching the 256-token output cap.
These are single synthetic retrieval checks, not proof of general reasoning or
coding accuracy across long documents.

The 32K run completed before temperature monitoring was added. The 64K run included
three two-minute rests early in prefill (approximately **6.05 minutes total**,
including a later brief suspension). Further rests were then disabled, and the
same request continued to completion. Generation occurred without pauses.
The successful 128K retry was configured to pause at 95 C for at least one minute
and resume below 80 C. Its peak sampled temperature was 93 C, so **no pauses
actually occurred**. Minimum sampled available system RAM was 14.06 GiB, and the
model unloaded normally after completion. This result does not explain the lower
temperature versus the earlier attempt or establish repeatability.
Different cooling policies and background workloads prevent a controlled speed
comparison. The observed 93 C peak does not establish a safe sustained temperature.

The practical result is that all three profiles can handle these near-limit inputs,
but their long first-response waits make these examples unsuitable for interactive
use when low latency matters. Use the larger profiles when the additional context
is worth that delay; keep 8K/16K as the everyday starting point.

Earlier guarded 64K and 128K attempts stopped at the configured 85 C threshold
despite resting before the requests. Both loaded with full reported GPU placement.
An earlier 128K continuous retry reached its 95 C cancellation threshold after
13.78 minutes, processing 37,888 tokens without generating an answer. It remains
in the evidence as an incomplete attempt, separate from the successful retry.
These thresholds are test settings, not hardware temperature ratings.

See the [full report and evidence](benchmarks/2026-09-27-context-results.md).
Keep 8K/16K for everyday use; the larger profiles remain opt-in. Timed breaks
between tests do not cap temperature during a single long request. The harness
samples temperature and offers either cancellation or optional Windows runner
pauses, with a runtime toggle for continuing without cooling rests.

### Thinking effort comparison

A second benchmark compared Ollama thinking effort `medium` and `high` at 16K,
32K, 64K and 128K. Both efforts returned all three synthetic retrieval codes in
each context. The 16K high run reached the shared 4,096-token thinking-plus-answer
cap: all codes were present, but its explanatory answer was cut off. The other
seven requests ended normally. These tests compare latency and resource use for
one retrieval task, not overall reasoning quality.

| Context | Effort | Prompt tokens | First thinking | First answer | Total | Combined output tok/s | Peak GPU | Min. available RAM | Pauses |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 16k | medium | 11,401 | 3m 28s | 8m 45s | 9m 24s | 7.47 | 91 C | 19.37 GiB | 0 |
| 16k | high | 11,443 | 3m 28s | 13m 22s | 13m 31s | 6.80 | 91 C | 22.49 GiB | 0 |
| 32k | medium | 26,962 | 9m 14s | 10m 12s | 11m 07s | 5.67 | 93 C | 21.65 GiB | 0 |
| 32k | high | 27,004 | 9m 12s | 18m 20s | 19m 04s | 6.30 | 93 C | 21.83 GiB | 0 |
| 64k | medium | 56,481 | 22m 44s | 23m 51s | 25m 06s | 4.80 | 93 C | 19.39 GiB | 0 |
| 64k | high | 56,523 | 22m 36s | 28m 17s | 29m 09s | 5.24 | 93 C | 19.35 GiB | 0 |
| 128k | medium | 113,910 | 60m 28s | 61m 49s | 63m 19s | 3.67 | 93 C | 14.15 GiB | 0 |
| 128k | high | 113,952 | 60m 42s | 72m 56s | 74m 01s | 4.16 | 93 C | 14.12 GiB | 0 |

The same prompt was used for medium and high within each context. Thinking and
answer shared a 4,096-token output budget. The run was configured to pause the
active runner at 95 C for at least 60 seconds and resume below 80 C; the measured
peak was 93 C, so no pauses occurred. See the [full report and per-run evidence](benchmarks/2026-09-28-thinking-multi-context/README.md)
for input sizes, method and finish reasons. Thinking traces are discarded; only
character counts and timing are retained. These single-task results do not
measure broad reasoning or coding quality.

## Switch profiles

Start an 8K chat:

```bash
bash scripts/use-profile.sh 8k
```

Type `/bye` to finish. Start a new 16K chat:

```bash
bash scripts/use-profile.sh 16k
```

The helper unloads the other installed SER8 context profiles and runs the selected one with
`--think=false --keepalive 15m`. No daemon restart is required. This opens a fresh
conversation; it does not transfer history from another session. Finish requests
in other clients before switching.

To start a chat directly, use the commands below. Unlike the helper, these do
not explicitly stop other profiles first:

```bash
OLLAMA_HOST=127.0.0.1:11434 ollama run ser8-qwen38:8k --think=false --keepalive 15m
# or
OLLAMA_HOST=127.0.0.1:11434 ollama run ser8-qwen38:16k --think=false --keepalive 15m
```

In a graphical Linux client, select the corresponding model name. For API clients,
set `think:false`, `keep_alive:"15m"`, and `stream:true`; avoid overriding the saved
model parameters. Thinking and streaming are request choices, not Modelfile settings.
There is no server-wide selected profile: each request chooses its model.

## Verify once on your Linux machine

After sending a message, use another terminal:

```bash
bash scripts/verify-profile.sh 8k   # or 16k
OLLAMA_HOST=127.0.0.1:11434 ollama ps
sudo journalctl -u ollama -b -n 200 --no-pager
```

Expect context 8192 or 16384 and full reported GPU placement. Inspect the logs for
the **Vulkan** backend and **MTP with draft length 2**; the placement check alone
cannot prove these. If runner arguments are logged, look for `draft-mtp` and
`--spec-draft-n-max 2`. Unsupported parameters, CPU fallback or absent MTP must be
resolved before treating this as the tested setup. The 780M uses shared system RAM;
reported GPU allocation is not dedicated VRAM. Close heavy apps and avoid duplicate
servers or runners. Keep one server and one model loaded during validation.

## Validation status

Profile-selection and context-verification regression tests run without a server:

```bash
python3 -m unittest discover -s tests -v
```

The large-context benchmark harness saves requests, responses, placement and
whole-system available-memory samples. It requires an idle local server with the
requested profiles already created and a new output directory:

```bash
python3 scripts/benchmark-context.py --output benchmarks/my-context-run
```

It runs 32K, 64K and 128K sequentially, with one smoke request and one long request
per profile, then unloads each model. `--profiles 32k` selects one profile. Before
each profile it rests for at least five minutes and waits for GPU temperature
below 70 C. Every five seconds it samples temperature; reaching 85 C cancels the
request and stops the sequence. These are conservative benchmark limits, not
hardware maximum ratings. Temperature monitoring uses the Windows graphics API
or Linux amdgpu hwmon; unavailable readings prevent an unmonitored run.

Use `--cooldown-seconds`, `--resume-below`, and `--max-gpu-temp` to adjust the
policy. Each request has a 90-minute limit by default (`--max-seconds`); available
RAM below 2 GiB for 30 seconds also cancels it. Creating a file named `STOP` in
the run's output directory requests cancellation. Streamed response events are
saved as they arrive. A cancelled request cannot resume mid-prefill and is not a
completed benchmark. By default, timed breaks occur between profiles; a long
individual request runs continuously unless a limit is reached.

On Windows, optional **in-request cooling pauses** preserve the active request.
Download [Microsoft Sysinternals PsSuspend](https://learn.microsoft.com/en-us/sysinternals/downloads/pssuspend)
and supply the path to `pssuspend64.exe` (the executable is not included here):

```powershell
python scripts/benchmark-context.py --profiles 64k --output benchmarks/my-paused-64k `
  --pause-tool C:\Tools\PsTools\pssuspend64.exe --work-seconds 300 --rest-seconds 120
```

This mode suspends only the matching single-model Ollama runner for two minutes
after five minutes of work, or sooner at the temperature threshold. It resumes
once the rest has elapsed and the GPU is below 70 C. Memory stays allocated;
the request and its processed context are retained. Keep the server dedicated to
this benchmark while it runs. `pauses.json` records each pause and resume.
Elapsed times and API timings include these pauses and must not be compared
directly with continuous-run throughput. Normal cleanup resumes the runner
before unloading it; if the harness is forcibly killed during a pause, use
`pssuspend64.exe -r <runner_pid>` with the PID recorded in `pauses.json` to resume
that runner. Model settings remain unchanged.

For temperature-triggered pauses only, set `--work-seconds 0`. For example,
`--max-gpu-temp 95 --rest-seconds 60 --resume-below 80` with `--pause-tool`
pauses the long request at 95 C, waits at least one minute, then resumes below
80 C. These configurable thresholds describe a test policy, not hardware ratings.
Without `--pause-tool`, reaching `--max-gpu-temp` cancels the request.

For runs started with the current harness, creating `NO_PAUSES` in the run's
output directory resumes any cooling pause and disables further pauses within
one sampling interval, without cancelling the request. Removing the file enables
pauses again. While disabled, the pause-mode temperature threshold does not stop
the request; temperature sampling, the time limit and the low-memory guard remain.


All four scripts passed Bash syntax checks during the documentation review on
2026-09-27. Repeat that check from the repository root with:

```bash
for script in scripts/*.sh; do
  bash -n "$script" || exit 1
done
```

Syntax checks do not execute the scripts or validate Ollama behavior. Earlier
setup notes reported mocked API/CLI checks, but their harness and results are
not included here and were not verified during this review. No real Linux SER8
GPU run has been verified for this repository. Use the runtime checks above to
validate your installation.

For comparable benchmark results, record the OS, driver and Ollama versions,
model digest, profile, exact prompt, request options, input/output token counts,
prompt-evaluation and generation durations, and whether the model and prompt
cache were warm. Keep the raw responses and repeat each measurement. Saved prompts, settings and responses are linked from the
[benchmark report](benchmarks/2026-09-26/README.md). The original benchmark
execution harness is not included; replaying the prompts requires recreating
the recorded request options and cache conditions.

For manual serving and undo instructions, see [LINUX-NOTES.md](LINUX-NOTES.md).

Sources (links reviewed 2026-09-27): [model tags](https://ollama.com/library/qwen3.8/tags),
[Linux](https://docs.ollama.com/linux), [GPU support](https://docs.ollama.com/gpu),
[Modelfiles](https://docs.ollama.com/modelfile), [chat API](https://docs.ollama.com/api/chat).
