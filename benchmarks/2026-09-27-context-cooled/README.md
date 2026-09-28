# Temperature-guarded 64K retry — 2026-09-27

After a five-minute cooldown, GPU temperature was about 40 C. The 64K profile
loaded successfully with a 65,536-token context and full reported GPU placement.
The smoke request completed in 13.10 seconds, including 11.27 seconds of loading.

The long request used the same 57,060-token synthetic input as the interrupted
original run. The temperature guard cancelled it after **210.50 seconds**, when
a five-second sample read **86 C**, exceeding the configured **85 C** limit.
There was no first output token or final API response. The last saved server
progress line records 11,008 processed tokens (about 19% of the input).
This is a thermal-limited attempt, not a completed context or retrieval result.

Minimum sampled available system RAM was **20.86 GiB**. The immediate constraint
was the chosen temperature limit, not lack of RAM. These limits are conservative
benchmark choices, not manufacturer temperature ratings. A sampled guard may
overshoot its threshold between readings and during cancellation.

Evidence: [settings](settings.json), [environment](environment.json),
[cooldown samples](64k-cooldown.json), [smoke result](64k/smoke-result.json),
[placement](64k/smoke-placement.json), [runner](64k/runner.json),
[long request](64k/long-request.json), [interruption result](64k/long-result.json),
[temperature/RAM samples](64k/long-memory.json), and
[server log excerpt](64k/abort-server-log.txt).

The result's false retrieval flags mean no answer was produced before cancellation;
they must not be interpreted as incorrect model answers. The model was unloaded
and the sequence stopped. The 128K attempt is recorded separately in
`../2026-09-27-context-128k-cooled/` after another cooldown.

The current harness also saves memory samples during execution, checks the
initial temperature before issuing a request, and supports a `STOP` file in its
output directory. Timed cooldowns happen before profiles. Reaching a temperature
limit cancels the active request; it does not pause and resume its computation.
