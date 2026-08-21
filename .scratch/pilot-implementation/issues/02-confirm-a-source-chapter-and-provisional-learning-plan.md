# 02 — Confirm a Source Chapter and provisional Learning Plan

**What to build:** A learner can inspect detected structure, correct the next Source Chapter span, choose an allowed duration policy, and receive a provisional Learning Plan of coherent Listening Sessions. Detailed extraction is limited to the confirmed span, and unsafe or uncertain boundaries remain visible instead of being guessed.

**Blocked by:** 01 — Import a Source Document into a traceable Book Workspace.

**Status:** resolved

- [x] The learner can select a detected Source Chapter and adjust its boundaries using adjacent context, printed and physical page references, and first/last-page previews.
- [x] Confirming a span starts detailed provenance-preserving extraction only for the material needed by the requested generation span.
- [x] The Source Index retains typed nodes, hierarchy, raw and normalized text, normalization operations, page geometry, evidence, warnings, and stable artifact hashes.
- [x] The default 15–25-minute policy and every valid custom Book Workspace policy produce an ordered provisional Learning Plan whose target is the range midpoint.
- [x] Invalid custom bounds are rejected, duration changes affect only ungenerated Episodes, and no Episode above 30 minutes can be approved without source-structure correction.
- [x] Packing preserves atomic semantic units, contiguous source coverage, hierarchy-aware boundaries, and explicit provisional cuts; a remaining short tail shows its pages, reason, revised plan length, and revised cost before approval.
- [x] HTTP-boundary tests prove span correction, extraction scoping, valid and invalid duration policies, coherent packing, short-tail approval, and blocked overlong behavior.
- [x] Traces and function documentation satisfy the spec's run correlation, bounded input/output representation, redaction, and human-oriented contract requirements.

## QA Summary

- Exercised the HTTP boundary with happy paths, invalid/non-finite duration policies,
  reversed and cross-chapter spans, strict-type violations, retries, short-tail approval,
  path traversal, and an indivisible unit above the hard 30-minute limit.
- Used the authorized *AI Engineering* PDF to reopen a retained workspace and plan physical
  pages 393–409: 102 typed nodes packed into one 22.67-minute session without an atomic cut.
- Interacted with the real browser UI using blank selection, invalid policy recovery,
  repeated confirmation, page reload/resume, and a 375-pixel viewport with no overflow.
- QA found and fixed three defects: subsection spans were incorrectly required to contain
  the top-level chapter heading, reload offered no way to resume a retained workspace, and
  successful plans rendered the complete 100k+ character Source Index instead of a bounded
  summary. Regression coverage was added for each behavior.
