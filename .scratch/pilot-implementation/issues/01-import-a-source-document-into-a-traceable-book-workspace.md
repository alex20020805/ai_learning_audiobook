# 01 — Import a Source Document into a traceable Book Workspace

**What to build:** A learner can use the private Mac application to import a native-text Source Document and receive a persistent Book Workspace. The Local Orchestrator validates the document, preserves it immutably, reopens identical content, distinguishes changed editions, performs a fast structural scan, and exposes the run and its evidence through the public HTTP boundary.

**Blocked by:** Wayfinder 10 — Decide the MVP architecture and provider routing; Wayfinder 11 — Decide the pilot acceptance contract.

**Status:** resolved

**Blocker disposition:** The user explicitly approved implementation on 2026-08-19 despite the open Wayfinder blockers.

- [x] Importing an acceptable native-text PDF creates a Book Workspace keyed by the Source Document content hash and preserves the original bytes unchanged.
- [x] Importing identical bytes reopens the existing Book Workspace, while changed bytes create a new linked Source Document edition.
- [x] Corrupt, password-blocked, and scan-heavy inputs are rejected with an actionable reason and no partially published workspace.
- [x] The import result exposes document identity, page count, structural-scan status, detected top-level structure, validation outcome, and warnings through the browser UI and HTTP boundary.
- [x] The learner-authorized reference PDF can be placed in ignored private test-data storage without being committed or redistributed; distributable tests use synthetic fixtures where practical.
- [x] An HTTP-boundary test proves create, reopen, changed-edition, and rejection behavior using isolated temporary Book workspaces and no network or billed provider access.
- [x] Every run, request, artifact, and named application-function call is correlated in structured traces; large values use type, size, hash, artifact reference, and bounded beginning/end previews, and secrets are redacted.
- [x] Every named function has human-oriented documentation covering inputs and requirements, behavior, side effects, output type, failure behavior, and callback contracts where applicable.

## Outcome

Implemented and verified on branch `codex/pilot-01-traceable-workspace`. The private browser UI imports native-text PDFs through the Local Orchestrator, requires explicit edition lineage, publishes immutable hash-keyed Book Workspaces atomically, exposes structural evidence and warnings, and retains correlated run/function/artifact traces. The learner-authorized 991-page reference PDF was copied to ignored private test data and passed the smoke import with 14 detected top-level headings. No paid provider was called.
