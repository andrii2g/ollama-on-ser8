# Qwen3.8 on a SER8 with 64 GB RAM

Recommended starting configuration for a Beelink SER8 with **Ryzen 7 8845HS,
Radeon 780M and 2 x 32 GB DDR5-5600**: Ollama, **27.3B Q4_K_M weights with MTP**,
Vulkan acceleration, and two saved context profiles.

**Evidence:** Windows benchmark artifacts from 2026-09-26 are included in
[the benchmark report](benchmarks/2026-09-26/README.md): measurements, settings,
prompts and saved API responses from Ollama 0.34.2. The test machine was the
Windows 11 SER8 described above.
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

Both use `num_thread=6`, `num_batch=256`, `draft_num_predict=2` and
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

## Switch profiles

Start an 8K chat:

```bash
bash scripts/use-profile.sh 8k
```

Type `/bye` to finish. Start a new 16K chat:

```bash
bash scripts/use-profile.sh 16k
```

The helper unloads the other SER8 profile and runs the selected one with
`--think=false --keepalive 15m`. No daemon restart is required. This opens a fresh
conversation; it does not transfer history from another session. Finish requests
in other clients before switching.

To start a chat directly, use the commands below. Unlike the helper, these do
not explicitly stop the other profile first:

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
