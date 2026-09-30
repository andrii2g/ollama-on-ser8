# Benchmarking guide

This document contains benchmark execution commands, run controls and output handling. The [root README](README.md) keeps the measured results and recommendations; detailed run-specific results and artifacts remain in the linked reports.

## What the runs measure

The context harness submits a synthetic prompt with retrieval codes near its beginning, middle and end. It saves request/response timing, GPU placement, five-second temperature samples and whole-system available-memory samples. It can run with thinking off, low, medium or high. Thinking trace text is discarded; final answers and aggregate thinking counts/timings are saved. These runs measure latency, resource use and a narrow retrieval condition, not general answer quality.

The thinking matrix uses identical prompts for medium and high within each context size, with scaled input lengths at 16K, 32K, 64K and 128K. It performs eight sequential long requests plus smoke checks, with one model/request at a time. Its 4,096 default `num_predict` cap is shared by thinking and answer.

The harness validates the selected profile's saved context, threads, batch, MTP draft count and temperature before running. It requires local Ollama and pre-created profiles. It does not install models, modify daemon settings or configure power and fan controls.

## Run the non-thinking context suite

Run from the repository root, against an idle local server with the requested profiles installed. Output must go to a new directory. The normal profile installer creates 8K and 16K; create larger profiles explicitly when needed:

```bash
bash scripts/apply-profiles.sh 32k 64k 128k
```

Then run the default 32K/64K/128K suite:

```bash
python3 scripts/benchmark-context.py --output benchmarks/my-context-run
```

The default suite runs 32K, 64K and 128K with thinking off and a 256-token combined output cap. Select profiles or override the request length as needed:

```bash
python3 scripts/benchmark-context.py --profiles 32k 64k --output benchmarks/my-run
python3 scripts/benchmark-context.py --profiles 64k --records 1505 --think medium \
  --num-predict 4096 --output benchmarks/my-64k-medium
```

Use `python3 scripts/benchmark-context.py --help` for all options. Requests have a default 90-minute time limit. By default, the harness waits at least five minutes before a profile and for GPU temperature below 70 C. It samples temperature every five seconds and cancels an unpaused request at 85 C. Reaching this cancellation threshold does not resume mid-request; prefill would need to be repeated. A `STOP` file in the run output directory requests cancellation. A memory guard also stops a run when available RAM remains below 2 GiB for 30 seconds.

Temperature thresholds are run policies, not hardware safety ratings. The integrated GPU uses shared system memory. Close unrelated GPU/RAM workloads and keep one model/request loaded for comparable runs.

## Run the thinking comparison

The complete four-context matrix is a Windows run that uses Microsoft Sysinternals PsSuspend to preserve an in-progress request if temperature pauses are needed. Download PsSuspend from Microsoft's official [Sysinternals page](https://learn.microsoft.com/en-us/sysinternals/downloads/pssuspend); the executable is not included in this repository.

```powershell
python scripts/benchmark-thinking.py `
  --output benchmarks/my-thinking-run `
  --pause-tool C:\Tools\PsTools\pssuspend64.exe
```

It runs medium and high for each context size, in order, with a 4,096 shared thinking-plus-answer token cap and a 90-minute per-request limit. Scheduled rests are off. The runner pauses at 95 C for at least 60 seconds and resumes after temperature falls below 80 C. No pauses are required when the threshold is not reached. An interrupted matrix can be resumed with `--resume`; it retains completed result folders and continues at the first unfinished case.

For a single context and custom policy, use `benchmark-context.py` directly. For example, a 64K medium request with the same 95/80 C policy is:

```powershell
python scripts/benchmark-context.py --profiles 64k `
  --output benchmarks/my-64k-medium `
  --pause-tool C:\Tools\PsTools\pssuspend64.exe `
  --work-seconds 0 --rest-seconds 60 `
  --cooldown-seconds 0 --max-gpu-temp 95 --resume-below 80 `
  --think medium --num-predict 4096
```

Without `--pause-tool`, hitting the temperature limit cancels the request. With a pause tool, `--work-seconds 0` disables scheduled rests and leaves only temperature-triggered pauses. When scheduled rests are enabled, the harness pauses after the selected work interval. The request and allocated context remain in the runner while suspended; do not use the same Ollama server for unrelated work during a pause.

## Output, evidence and checks

Each run directory contains settings, request/response files, per-request results, placement, memory, temperature and pause records. `summary.json` collects matrix results. The stream file strips `thinking` fields; response JSON and text retain the final answer only. Review saved prompts and responses before publishing any custom run, because prompts can contain private code or documents. The checked-in synthetic run contains no detected secrets.

Test profile and temperature helpers without a live server:

```bash
python3 -m unittest discover -s tests -v
```

Run shell syntax checks from the repository root:

```bash
for script in scripts/*.sh; do
  bash -n "$script" || exit 1
done
```

A passing unit or syntax test does not establish Ollama behavior. Confirm full Vulkan placement, model settings and GPU access on the target host. No Linux SER8 GPU run has been measured for this repository.

## Reports

- [2026-09-26 baseline benchmark report](benchmarks/2026-09-26/README.md)
- [2026-09-27 context results and excluded attempts](benchmarks/2026-09-27-context-results.md)
- [2026-09-28 thinking-enabled comparison](benchmarks/2026-09-28-thinking-multi-context/README.md)
