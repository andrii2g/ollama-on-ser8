# Temperature-guarded 128K attempt — 2026-09-27

After a five-minute cooldown to about 40 C, `ser8-qwen38:128k` loaded and answered
the smoke prompt. The allocated context was **131,072 tokens**, with full reported
GPU placement. The smoke request took **11.04 seconds**, including **9.35 seconds**
of loading; its sampled GPU peak was **57 C**. Runner logs showed an **8 GiB** main
f16 KV buffer and an additional **512 MiB** KV buffer for MTP.

The long synthetic prompt contained **115,451 tokens** according to the server's
tokenizer. The guard cancelled the request after **210.50 seconds** when a sample
reached **85 C**. No first output token or final API response was received.
Minimum sampled available system RAM was **16.52 GiB**.

This validates loading the 128K allocation, not successful retrieval across a
115K-token prompt. No complete prefill duration, generation throughput or retrieval
score is claimed. The false retrieval flags in the interruption result mean no
answer was produced, not that the model answered incorrectly.

Evidence: [settings](settings.json), [environment](environment.json),
[cooldown](128k-cooldown.json), [smoke result](128k/smoke-result.json),
[placement](128k/smoke-placement.json), [runner](128k/runner.json),
[long request](128k/long-request.json), [interruption result](128k/long-result.json),
[temperature/RAM samples](128k/long-memory.json), and
[server log excerpt](128k/abort-server-log.txt).

The model was unloaded after cancellation. The 85 C cutoff is a conservative test
policy, not a manufacturer rating. Temperatures were sampled every five seconds
through the Windows graphics API; CPU temperatures were not measured. The run
used the same weights, f16 cache, MTP draft 2, six threads and batch 256 as the
other profiles. See [the comparison](../2026-09-27-context-results.md).
