# 03 — Generate one retained verbatim Episode

**What to build:** From a confirmed Listening Session, a learner can run one complete Episode Generation Job through extraction, verbatim scripting, deterministic test speech, assembly, validation, and local publication. The result is useful for exercising the full product path without a network call or paid credit.

**Blocked by:** 02 — Confirm a Source Chapter and provisional Learning Plan.

**Status:** ready-for-agent

- [ ] Starting generation creates an independent versioned Episode Generation Job pinned to immutable source, boundary, duration, prompt, schema, and provider-policy versions.
- [ ] One visible durable FIFO queue allows at most one active job and exposes every normal lifecycle transition through the browser UI and HTTP boundary.
- [ ] The verbatim Faithful Track script preserves all substantive source material, contains no outside explanation, and records every allowed normalization or non-prose treatment in the Transformation Report.
- [ ] Deterministic fake model and speech adapters produce a valid assembled audio artifact without network access or paid usage.
- [ ] Validation prevents publication unless the script, transcript page references, Transformation Report, audio artifact, provider provenance, cost record, and trace manifest are complete.
- [ ] The complete ready result remains in the Book Workspace and can be inspected through the private application.
- [ ] An HTTP-boundary test exercises the entire happy path from confirmed span to retained Episode and asserts externally visible state and artifacts rather than private call order.
- [ ] Traces make every stage, application function, input, output, artifact, and validation reconstructable while applying bounded previews and secret redaction; all named functions satisfy the documentation contract.
