# 02 — Confirm a Source Chapter and provisional Learning Plan

**What to build:** A learner can inspect detected structure, correct the next Source Chapter span, choose an allowed duration policy, and receive a provisional Learning Plan of coherent Listening Sessions. Detailed extraction is limited to the confirmed span, and unsafe or uncertain boundaries remain visible instead of being guessed.

**Blocked by:** 01 — Import a Source Document into a traceable Book Workspace.

**Status:** ready-for-agent

- [ ] The learner can select a detected Source Chapter and adjust its boundaries using adjacent context, printed and physical page references, and first/last-page previews.
- [ ] Confirming a span starts detailed provenance-preserving extraction only for the material needed by the requested generation span.
- [ ] The Source Index retains typed nodes, hierarchy, raw and normalized text, normalization operations, page geometry, evidence, warnings, and stable artifact hashes.
- [ ] The default 15–25-minute policy and every valid custom Book Workspace policy produce an ordered provisional Learning Plan whose target is the range midpoint.
- [ ] Invalid custom bounds are rejected, duration changes affect only ungenerated Episodes, and no Episode above 30 minutes can be approved without source-structure correction.
- [ ] Packing preserves atomic semantic units, contiguous source coverage, hierarchy-aware boundaries, and explicit provisional cuts; a remaining short tail shows its pages, reason, revised plan length, and revised cost before approval.
- [ ] HTTP-boundary tests prove span correction, extraction scoping, valid and invalid duration policies, coherent packing, short-tail approval, and blocked overlong behavior.
- [ ] Traces and function documentation satisfy the spec's run correlation, bounded input/output representation, redaction, and human-oriented contract requirements.
