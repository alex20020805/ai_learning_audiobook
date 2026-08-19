# 05 — Recover and supersede Episode Generation Jobs safely

**What to build:** A learner can cancel, retry, or replace Episode generation without corrupting retained state or accidentally publishing work based on obsolete choices. Compatible checkpoints are reused, incompatible work is invalidated explicitly, and interrupted jobs remain fully explainable.

**Blocked by:** 03 — Generate one retained verbatim Episode.

**Status:** ready-for-agent

- [ ] A cancellation request allows the current atomic write to finish, publishes no partial Episode, and ends in a consistent visible terminal state.
- [ ] A retry resumes only checkpoints whose source, policy, prompt, schema, provider configuration, and upstream artifact hashes remain compatible.
- [ ] Changed source, span, duration, prompt, or provider policy makes affected queued work stale rather than silently reusing it.
- [ ] A running superseded job cannot become the current Episode without explicit approval, and its artifacts remain distinguishable from the current result.
- [ ] Failed, cancelled, stale, and superseded jobs retain their causal history, errors, checkpoints, costs, and artifact dispositions.
- [ ] HTTP-boundary tests prove cancellation during each durable stage, compatible retry, incompatible retry, queued-job staleness, and running-job supersession.
- [ ] Traces identify the exact compatibility decision and before/after state without duplicating large source or binary values.
- [ ] Every named function and callback involved in queueing, checkpointing, cancellation, retry, and supersession satisfies the documentation contract.

