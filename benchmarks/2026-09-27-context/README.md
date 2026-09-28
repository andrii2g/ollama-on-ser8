# Excluded initial 32K attempt

The 32K smoke request completed and confirmed that the profile could load.
The subsequent 900-record prompt contained 33,701 input tokens, exceeding the
32,768-token allocation. Ollama logged truncation to 16,386 tokens; see
[the recorded warning](truncation.txt). The long request was cancelled during
prefill and has no completed response or throughput result.

This attempt is excluded from successful-context results. The corrected run in
[the second attempt](../2026-09-27-context-v2/README.md) uses 760/1,520/3,040
records for 32K/64K/128K and explicit request-level context settings. Its smoke
request uses the same short prompt. The initial settings file records the
original, oversized record counts for auditability.
