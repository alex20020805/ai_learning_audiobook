# Prototype hierarchy-aware Episode packing

Type: prototype
Status: resolved
Blocked by: 01, 04

## Question

Using the reference book, what packing behavior produces coherent 20-minute Episodes within the 15–25 minute bounds while respecting chapters, subsections, arguments, examples, code, figures, and page traceability? Produce a rough plan for the user to inspect rather than implementing the production pipeline.

## Answer

Use a hierarchy-aware global partitioner over ordered atomic SourceNodes. Keep 15–25 minutes as a hard duration window with 20 minutes as the optimization target. Prefer complete chapter boundaries, then accepted outline/semantic boundaries; cross chapters when that prevents an undersized tail. Never silently split an indivisible argument, example, code block, table, or figure. When the available extraction is too coarse to prove a safe boundary, expose the cut as provisional and require SourceNode-level validation before generation.

The accepted prototype used real outline and page-word data from *AI Engineering*. At the default 140 words per minute it produced 55 Episodes totaling approximately 18 hours 55 minutes, with no short tails or unresolved duration failures and 17 explicitly provisional page-level boundaries. The math and code/visual stress slices each remained intact within the duration window. The user accepted this behavior on 2026-08-15.

The disposable implementation remains on branch `prototype/episode-packing`: initial behavior commit `c3fb03e`, documented-function commit `cd7ac61`. It is decision evidence, not production code, and is intentionally not merged into the main branch.

## Superseded assumption

Ticket 06 generalizes the prototype's fixed 15–25-minute hard window into the product's default duration policy. Its hierarchy-aware global partitioning, semantic-boundary preference, and explicit handling of unverified splits remain accepted. Custom bounds and approved short-tail exceptions are defined in [the local-first workflow decision](./06-decide-the-local-first-product-workflow.md).
