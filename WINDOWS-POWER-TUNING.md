# Windows power and GPU frequency control on SER8

Researched 2026-09-27 for this project's Windows 11, Ryzen 7 8845HS,
Radeon 780M, 64 GB DDR5-5600 configuration. This is a research and operating
guide, not evidence that the settings below have been tested on this unit.
No tuning software was installed and no hardware settings were changed.

## What can be controlled on demand?

| Control | Windows route | Runtime behavior / limitation |
|---|---|---|
| Shared APU power budget | UXTU custom presets; RyzenAdj CLI | Can request new limits without rebooting; firmware may clamp or overwrite them |
| CPU temperature target | UXTU or RyzenAdj `tctl-temp` | CPU control target; not a GPU-temperature cutoff |
| GPU static boost clock | UXTU iGPU Clock; RyzenAdj `gfx-clk` | Supported code path for Hawk Point; must verify hardware response |
| GPU maximum cap with normal automatic scaling | Not established for this SER8 | Do not confuse it with the static-clock control |
| BIOS power profile | Firmware setup | Boot-time baseline; not a convenient runtime switch |
| Windows power mode | Windows settings | Changes performance policy, not a precise GPU MHz or package watt limit |

The CPU, GPU and other parts of the APU share a package power budget.
A 45 W package limit is neither a 45 W GPU allowance nor a 45 W wall-socket
limit. Lowering the GPU clock also does not guarantee a lower package temperature:
CPU activity can use some of the available headroom.

## Preferred Windows starting point: UXTU

Use [Universal x86 Tuning Utility's official GitHub releases](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility/releases).
The latest stable release observed during research was **26.3.1**. Its prerequisites
are .NET Desktop Runtime 10 x64, PawnIO and the Microsoft Visual C++ Redistributable.
Current releases removed the legacy WinRing0/InpOutx64 dependencies. Follow the
requirements for the exact release downloaded; old tutorials describe a different stack.

UXTU's versioned source explicitly exposes iGPU tuning for Hawk Point and includes
runtime power commands. That establishes implementation support, not successful
operation on every Beelink BIOS.

Suggested manual workflow:

1. Record BIOS version, AMD graphics driver version, current power limits and a
   baseline sensor log. Keep the existing BIOS profile unchanged initially.
2. Open UXTU with the privileges its hardware access requires. Leave automatic
   startup, automatic reapply and adaptive tuning disabled for the first tests.
3. In Custom Presets, enable only the intended settings. Create a power-only
   preset with STAPM, Slow and Fast power limits set to the same test value.
4. Save the preset, then explicitly Apply it. Saving alone is not applying.
5. Check actual package power and performance under a repeatable load.
6. Save other validated presets and select/apply them when needed.

Candidate experiments, provided each is no higher than the recorded baseline:

| Preset name | STAPM / Slow / Fast | GPU clock |
|---|---|---|
| Power-45W | 45 / 45 / 45 W | Leave automatic |
| Power-40W | 40 / 40 / 40 W | Leave automatic |
| Power-35W | 35 / 35 / 35 W | Leave automatic |

These are proposed comparisons, not measured performance recommendations.
Setting all three alike avoids deliberately allowing a higher fast power budget;
it does not promise zero transient overshoot. A limit is a ceiling, not a request
to consume that much power.

An unchecked control usually means "do not write this setting", not "restore its
default". A baseline preset must explicitly restore previously changed power
values. Do not label an empty preset "Stock" and assume it resets hardware.

Sources: [preset UI](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility/blob/26.3.1/Universal%20x86%20Tuning%20Utility/Views/Pages/CustomPresets.xaml),
[preset implementation](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility/blob/26.3.1/Universal%20x86%20Tuning%20Utility/Views/Pages/CustomPresets.xaml.cs),
[SMU backend](https://github.com/JamesCJ60/Universal-x86-Tuning-Utility/blob/26.3.1/Universal%20x86%20Tuning%20Utility/Scripts/AMD%20Backend/RyzenSmu.cs).

## Scriptable package limits: RyzenAdj

[RyzenAdj](https://github.com/FlyGoat/RyzenAdj) provides a Windows CLI requiring
Administrator access. Version 0.19.0 was the latest release observed. Use its
[official releases](https://github.com/FlyGoat/RyzenAdj/releases), retaining the
required companion files. Older Windows driver dependencies can be blocked by
Windows security; if initialization fails, prefer the current UXTU/PawnIO route
over disabling system protections just to use an old driver.

Run from the extracted RyzenAdj directory in an elevated PowerShell:

```powershell
# Inspect support and save baseline before any writes.
.\ryzenadj.exe --help
.\ryzenadj.exe --info | Tee-Object -FilePath .\ser8-before.txt

# Example: request a 45 W package budget, only if <= baseline.
.\ryzenadj.exe --stapm-limit=45000 --slow-limit=45000 --fast-limit=45000
.\ryzenadj.exe --info

# Example: switch to 40 W without rebooting.
.\ryzenadj.exe --stapm-limit=40000 --slow-limit=40000 --fast-limit=40000
.\ryzenadj.exe --info
```

Power arguments use **milliwatts**: 45000 means 45 W. `slow-limit` is an averaged
package limit; `fast-limit` controls the faster limit; STAPM is a sustained thermal
power mechanism whose effective behavior varies by platform. `--tctl-temp=85`
is a separate optional CPU temperature-target experiment, not an assurance that
every sensor stays below 85 C. Test it separately from power changes.

Source implementation includes Hawk Point power and forced-GPU-clock commands.
Firmware can still reject a setting, and a successful process exit is not proof
it took effect. Inspect reported values and independently measure behavior.
An unavailable PM table can prevent `--info` from working even when writes work;
that is not permission to assume unknown baseline values.

Sources: [CLI source](https://github.com/FlyGoat/RyzenAdj/blob/master/main.c),
[hardware API](https://github.com/FlyGoat/RyzenAdj/blob/master/lib/api.c),
[monitoring options](https://github.com/FlyGoat/RyzenAdj/wiki/Options),
[Windows troubleshooting](https://github.com/FlyGoat/RyzenAdj/wiki/FAQ).

## GPU frequency: static request versus maximum cap

An important correction to the earlier chat advice: a convenient maximum GPU
clock cap with automatic scaling has **not** been established for this machine.
RyzenAdj's `max-gfxclk` implementation does not include Hawk Point or Phoenix.
The different `gfx-clk` command does include those families; its CLI calls it a
forced clock. The CLI's "Renoir Only" description is narrower than the current
implementation, so installed build and actual response must be checked.

UXTU calls its corresponding option **iGPU Clock (MHz)** under **iGPU Tuning**.
Its source describes a static boost clock and says a reboot or sleep is needed
to revert to normal. This is not a promise of an exact clock under all power,
temperature and idle conditions.

For a controlled experiment:

1. Measure GPU frequency during the demanding prefill portion of the workload.
2. Choose a request about 10-15% below that observed frequency. For example,
   2200 MHz is a candidate only when the baseline is appreciably above it.
3. Enable only iGPU Clock alongside an already validated package-power preset.
   Leave voltage offsets, curve optimization, current limits, memory/fabric
   clocks and other tuning untouched.
4. Apply and confirm the GPU clock actually changes. Measure power, temperature
   and throughput again, including idle behavior after the request finishes.

Conditional CLI equivalent for a build exposing `gfx-clk`:

```powershell
# Experimental static GPU clock request; not a maximum-frequency cap.
.\ryzenadj.exe --gfx-clk=2200
```

Another supported frequency request can be applied at runtime, but returning to
automatic operation is a separate problem. Disable reapply/startup tuning and
restart Windows to restore the firmware baseline, then verify clocks and power.
UXTU also documents sleep as a reset route; verify it on this unit rather than
depending on it. Unchecking the setting or closing the app does not necessarily
undo the previous write. Do not assume `--gfx-clk=0` is a supported reset.

## Persistence and automation

Start with manual application. Firmware, resume, restart or other software may
replace settings. Check after a few minutes and after any power-state change.
Use one tuning program at a time; competing automatic writers make tests unclear.

Once validated, power-only presets are suitable for desktop shortcuts or manually
triggered elevated Scheduled Tasks. Give each task an explicit executable path
and fixed, reviewed arguments. RyzenAdj also supplies a reapplication script and
Task Scheduler example; enable recurring writes only if measurements show they
are necessary. Log requested values, readback and failures.

A genuinely reversible runtime GPU-cap toggle remains unverified. Static GPU
profiles are usable experiments, but the documented reset requirement makes
package-power profiles the better first choice for daily on-demand control.

## How to evaluate this project's Ollama workload

Keep the model, context, prompt, batch, threads and MTP settings identical.
Measure **prompt processing/prefill** and **token generation** separately, and
record cache use. A GPU reduction may affect these phases differently; this
must be measured rather than inferred from GPU utilization alone.

For each profile, log:

- CPU Tctl/Tdie and GPU temperature as separately named sensors.
- Actual GPU clock, package power and any thermal/power limit indicators.
- RAM clock, to catch an unintended change, and SSD temperature where available.
- Prefill tokens/second, generation tokens/second, time to first token and errors.
- Ambient conditions and steady-state temperatures under the same cooling setup.

Repeat promising comparisons, then extend the best candidate to a sustained run.
Mark every profile switch in the log; do not mix two profiles into one benchmark
result. The first goal is to find the lowest power that preserves acceptable
performance, not to maximize every adjustable value.

The existing `scripts/gpu_temperature.py` reads Windows adapter GPU temperature
through D3DKMT, not CPU Tctl/Tdie. AMD's **100 C Tjmax** for the 8845HS is a CPU
junction specification; it must not automatically become the cutoff for that GPU
sensor. The saved 85 C guard is an experimental policy, not a claimed hardware
maximum. No benchmark guards were changed as part of this research.

Sources: [8845HS specifications](https://www.amd.com/en/products/processors/laptop/ryzen/8000-series/amd-ryzen-7-8845hs.html),
[Windows adapter temperature field](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/d3dkmthk/ns-d3dkmthk-_d3dkmt_adapter_perfdata).

## Other controls and remaining checks

AMD Adrenalin tuning is configuration-dependent; desktop Radeon screenshots do
not establish that a 780M has the same sliders. Check Performance/Tuning in a full
installation, but do not assume the absence of a control is a fault.
[AMD's tuning guide](https://www.amd.com/en/resources/support-articles/faqs/DH3-020.html)
explicitly qualifies feature availability. Ryzen Master is not the established
route for this mobile-class 8845HS, and Windows processor-state percentages are
not direct GPU MHz or watt controls.

Before calling any profile verified, establish the actual BIOS version, graphics
driver, current limits, CPU and GPU sensor readings, and whether the chosen tool
applies and retains the requested values. This research verifies software paths;
the SER8-specific measurements still need to be performed.
