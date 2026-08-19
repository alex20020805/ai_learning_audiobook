# 07 — Deliver and inspect a complete offline Episode

**What to build:** A learner can inspect all trust evidence for a finished Episode, copy its M4A to an approved iCloud Drive output folder, see an accurate delivery outcome, and unlock the next Listening Session without starting another generation job.

**Blocked by:** 04 — Resolve extraction warnings through evidence-backed review; 05 — Recover and supersede Episode Generation Jobs safely; 06 — Generate through the selected real provider routes.

**Status:** ready-for-agent

- [ ] The complete result view exposes the player and M4A, transcript with page references, Transformation Report, validation results, provider/runtime provenance, cost, run trace, and delivery status.
- [ ] Delivery copies only the finished M4A to the explicitly configured iCloud Drive output folder and never removes the complete local result.
- [ ] A successful copy records delivery but does not claim that the iPhone retained the file offline.
- [ ] Delivery failure leaves the ready Episode intact, presents an actionable error, and supports a traceable retry without regenerating the Episode.
- [ ] Successful pilot delivery completes the current Listening Session and unlocks, but does not start, the next Episode.
- [ ] In-app status and optional macOS notifications cover review, paid approval, failure, readiness, and delivery without leaking source content or credentials.
- [ ] HTTP-boundary tests prove successful and failed delivery, idempotent retry, retained-result integrity, and the next-session unlock rule using an isolated destination.
- [ ] Delivery, notification, and result-inspection functions and callbacks satisfy the traceability and human-oriented documentation contracts.

