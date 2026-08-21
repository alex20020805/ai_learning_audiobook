# 04 — Resolve extraction warnings through evidence-backed review

**What to build:** A learner can understand and resolve uncertain source handling without allowing fidelity failures to pass silently. Jobs pause with page-level evidence, support correction and compatible reruns, and continue automatically only when the confirmed outcome is safe.

**Blocked by:** 03 — Generate one retained verbatim Episode.

**Status:** resolved

- [x] Every warning is classified as `blocking`, `review_required`, or `informational`, and the displayed severity agrees with job behavior.
- [x] Blocking fidelity conditions cannot be approved away and never reach scripting or Speech Synthesis.
- [x] A review-required state shows affected pages, extracted source, proposed handling, evidence, expected impact, and the permitted correction, rerun, approval, or cancellation actions.
- [x] Approval is permitted only for interpretations that do not compromise the Faithful Track boundary, and the decision is tied to the exact warning and input versions.
- [x] Clean jobs continue without unnecessary intervention, while informational warnings remain visible in the final evidence.
- [x] HTTP-boundary tests prove blocking, review, correction, rerun, safe approval, cancellation, and automatic clean-path behavior with deterministic fixtures.
- [x] Each warning, learner decision, affected artifact, and resumed transition is connected to the original run and job in structured traces.
- [x] Every named function and callback involved in review and resumption satisfies the required human-oriented documentation contract.

## QA Summary

- Exercised blocking, review-required, informational, and clean paths at the HTTP boundary, including malformed corrections, safe approval, rerun, cancellation, and immutable correction overlays tied to exact input versions.
- Proved blocking warnings cannot be approved and produce neither script nor speech artifacts; proved informational warnings continue into final Episode evidence.
- Used the retained real-book fixture in the browser to recover a paused review after reload, reject a blank correction without stranding the controls, approve a safe interpretation, resume job version 3 into ready version 4, and stream the resulting audio with HTTP range requests.
- Found that retained Episode summaries hid resolved warning and decision counts. Added those bounded fields to the UI and a regression assertion, then repeated the browser reload successfully.
