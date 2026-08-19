# 04 — Resolve extraction warnings through evidence-backed review

**What to build:** A learner can understand and resolve uncertain source handling without allowing fidelity failures to pass silently. Jobs pause with page-level evidence, support correction and compatible reruns, and continue automatically only when the confirmed outcome is safe.

**Blocked by:** 03 — Generate one retained verbatim Episode.

**Status:** ready-for-agent

- [ ] Every warning is classified as `blocking`, `review_required`, or `informational`, and the displayed severity agrees with job behavior.
- [ ] Blocking fidelity conditions cannot be approved away and never reach scripting or Speech Synthesis.
- [ ] A review-required state shows affected pages, extracted source, proposed handling, evidence, expected impact, and the permitted correction, rerun, approval, or cancellation actions.
- [ ] Approval is permitted only for interpretations that do not compromise the Faithful Track boundary, and the decision is tied to the exact warning and input versions.
- [ ] Clean jobs continue without unnecessary intervention, while informational warnings remain visible in the final evidence.
- [ ] HTTP-boundary tests prove blocking, review, correction, rerun, safe approval, cancellation, and automatic clean-path behavior with deterministic fixtures.
- [ ] Each warning, learner decision, affected artifact, and resumed transition is connected to the original run and job in structured traces.
- [ ] Every named function and callback involved in review and resumption satisfies the required human-oriented documentation contract.
