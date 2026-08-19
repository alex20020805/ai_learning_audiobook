# 06 — Generate through the selected real provider routes

**What to build:** A learner can generate an Episode through the stage-specific real text and speech routes selected by the decision work. Local and hosted attempts use common validated contracts, separately billed fallbacks remain approval-gated, and the result records reproducible provider, cost, chunk, and assembly evidence.

**Blocked by:** 03 — Generate one retained verbatim Episode.

**Status:** ready-for-agent

- [ ] The selected local and hosted adapters consume equivalent versioned requests and return validated provider-neutral results for their assigned stages.
- [ ] Exact model/runtime, voice, prompt, schema, decoding or synthesis settings, input hashes, timestamps, latency, and metered cost are recorded for each attempt.
- [ ] Subscription unavailability or rate limiting pauses in `awaiting_paid_approval`; it never activates separately billed API usage automatically.
- [ ] Paid approval identifies the exact job, stage, provider/model, reason, incremental estimate, projected book total, and one authorized attempt.
- [ ] The US$1 per Episode and US$25 per book ceilings are enforced unless the learner explicitly approves an override.
- [ ] Speech is rendered from the approved script in shared sentence/paragraph chunks, assembled from 24 kHz WAV with source-aware offsets, and encoded as AAC-LC/M4A.
- [ ] Deterministic contract tests cover every adapter without network access; real-provider evaluation runs only through an explicit operator action and never as part of the ordinary automated suite.
- [ ] Provider requests and responses are traceable using bounded previews, hashes, artifact references, and credential redaction; every named adapter function and callback satisfies the documentation contract.
