# Design the fidelity and listening evaluation

Type: research
Status: resolved
Blocked by: none

## Question

What evidence-backed evaluation rubric should compare extraction, hierarchy-aware packing, verbatim scripts, listening-adapted scripts, visual narration, hosted-versus-local model outputs, and hosted-versus-local speech? Define measurable thresholds and a human review protocol for three structurally different selections from the reference book.

## Answer

Use a gated, slice-based rubric: zero-tolerance trust failures cannot be averaged
away by listening quality, and provider preference is considered only after every
candidate passes the same extraction, structure, script, visual, and speech gates.
The three pilot slices cover prose/hierarchy (PDF pp. 393-409), mathematical
notation (PDF p. 240 at `Understanding Language Modeling Metrics` through p. 252
before `Exact Evaluation`), and code/visuals (p. 252 at `Exact Evaluation` through
p. 266). Compare text models with two blinded runs per slice and speech engines on
identical approved scripts using one-minute P.85-inspired clips plus a full-Episode
endurance pass. Exact thresholds, gold-packet construction, reviewer protocol, and
stage-routing rules are in
[`../research/04-fidelity-and-listening-evaluation.md`](../research/04-fidelity-and-listening-evaluation.md).
