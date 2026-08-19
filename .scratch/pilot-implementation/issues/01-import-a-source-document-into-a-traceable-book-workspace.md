# 01 — Import a Source Document into a traceable Book Workspace

**What to build:** A learner can use the private Mac application to import a native-text Source Document and receive a persistent Book Workspace. The Local Orchestrator validates the document, preserves it immutably, reopens identical content, distinguishes changed editions, performs a fast structural scan, and exposes the run and its evidence through the public HTTP boundary.

**Blocked by:** Wayfinder 10 — Decide the MVP architecture and provider routing; Wayfinder 11 — Decide the pilot acceptance contract.

**Status:** ready-for-agent

- [ ] Importing an acceptable native-text PDF creates a Book Workspace keyed by the Source Document content hash and preserves the original bytes unchanged.
- [ ] Importing identical bytes reopens the existing Book Workspace, while changed bytes create a new linked Source Document edition.
- [ ] Corrupt, password-blocked, and scan-heavy inputs are rejected with an actionable reason and no partially published workspace.
- [ ] The import result exposes document identity, page count, structural-scan status, detected top-level structure, validation outcome, and warnings through the browser UI and HTTP boundary.
- [ ] The learner-authorized reference PDF can be placed in ignored private test-data storage without being committed or redistributed; distributable tests use synthetic fixtures where practical.
- [ ] An HTTP-boundary test proves create, reopen, changed-edition, and rejection behavior using isolated temporary Book workspaces and no network or billed provider access.
- [ ] Every run, request, artifact, and named application-function call is correlated in structured traces; large values use type, size, hash, artifact reference, and bounded beginning/end previews, and secrets are redacted.
- [ ] Every named function has human-oriented documentation covering inputs and requirements, behavior, side effects, output type, failure behavior, and callback contracts where applicable.

