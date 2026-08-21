# 03 — Generate one retained verbatim Episode

**What to build:** From a confirmed Listening Session, a learner can run one complete Episode Generation Job through extraction, verbatim scripting, deterministic test speech, assembly, validation, and local publication. The result is useful for exercising the full product path without a network call or paid credit.

**Blocked by:** 02 — Confirm a Source Chapter and provisional Learning Plan.

**Status:** resolved

- [x] Starting generation creates an independent versioned Episode Generation Job pinned to immutable source, boundary, duration, prompt, schema, and provider-policy versions.
- [x] One visible durable FIFO queue allows at most one active job and exposes every normal lifecycle transition through the browser UI and HTTP boundary.
- [x] The verbatim Faithful Track script preserves all substantive source material, contains no outside explanation, and records every allowed normalization or non-prose treatment in the Transformation Report.
- [x] Deterministic fake model and speech adapters produce a valid assembled audio artifact without network access or paid usage.
- [x] Validation prevents publication unless the script, transcript page references, Transformation Report, audio artifact, provider provenance, cost record, and trace manifest are complete.
- [x] The complete ready result remains in the Book Workspace and can be inspected through the private application.
- [x] An HTTP-boundary test exercises the entire happy path from confirmed span to retained Episode and asserts externally visible state and artifacts rather than private call order.
- [x] Traces make every stage, application function, input, output, artifact, and validation reconstructable while applying bounded previews and secret redaction; all named functions satisfy the documentation contract.

## QA Summary

- Exercised the public path from import and confirmed plan through all eight normal job
  transitions, retained inspection, queue inspection, audio streaming, and run-trace reading.
  The full suite passes with exact node-for-node script coverage and 24 kHz WAV validation.
- Challenged traversal identifiers, strict boolean/integer coercion, unknown sessions/plans,
  duplicate generation, an already-active queue, and a corrupted Source Index. Rejections
  allocate no new FIFO entry and publish no partial Episode.
- Generated the authorized real-book selection at physical pages 393–409: 102 verbatim
  source-linked segments, 23.64 seconds of deterministic test audio, zero network/paid usage,
  complete validation, and two FIFO-ordered independent job versions on repeat.
- Browser QA covered rapid-repeat protection, playable audio (`readyState=4`), reload/resume,
  explicit refresh, retained Episode inspection, and a 375-pixel viewport without overflow.
- QA found and fixed two defects: streamed `FileResponse` objects crashed the existing tracer,
  and corrupt session-to-source coverage could otherwise allocate a partial active job. Both
  now have permanent regression tests.
