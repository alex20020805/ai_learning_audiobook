# Decide the local-first product workflow

Type: grilling
Status: resolved
Blocked by: 01, 02, 03

## Question

What exact user and job-state workflow should the private browser UI and Local Orchestrator expose from PDF import through chapter confirmation, on-demand generation, warnings, transcript and Transformation Report review, iPhone download, check-in, and next-Episode generation?

## Answer

Use a persistent Book workspace keyed by the immutable Source Document's content hash. An identical import reopens the existing workspace instead of creating a duplicate; changed bytes create a new linked edition. Import first performs native-PDF validation and a fast structural scan, then shows detected chapters and a provisional Learning Plan. Detailed extraction is deferred to the selected generation span. The user confirms only that span through editable page boundaries, adjacent-boundary context, first/last-page previews, and a recomputed Episode estimate.

Duration policy belongs to the Book workspace. The default remains 15–25 minutes with a 20-minute target. Custom bounds must satisfy `5 <= minimum < maximum <= 30` and `5 <= maximum - minimum <= 10`; the midpoint is the target. Repacking changes only ungenerated Episodes. Hierarchy-aware packing first tries to avoid short tails, including crossing chapter boundaries when appropriate. A remaining short semantic tail pauses for explicit approval with its duration, pages, reason, revised plan length, and revised cost. No Episode may exceed 30 minutes; an indivisible overlong unit requires source-structure review.

Keep Document Processing Jobs separate from Episode Generation Jobs. Each Listening Session maps to one planned Episode, and each Episode has an independent, versioned Generation Job. Run one active job at a time through a visible FIFO queue with durable checkpoints. Normal jobs progress automatically after span confirmation:

`draft -> awaiting_span_confirmation -> queued -> extracting -> scripting -> synthesizing -> assembling -> validating -> ready -> delivering -> delivered`

Interruptions use `awaiting_review`, `awaiting_paid_approval`, `stale`, `failed`, `cancel_requested`, `cancelled`, or `superseded`. Cancellation finishes the current atomic write without publishing a partial lesson; retry resumes only compatible checkpoints. Jobs stay pinned to immutable source, boundary, duration, prompt, and provider-policy versions. A changed source version makes queued jobs stale and prevents a running superseded job from becoming the current lesson without explicit approval.

Warnings are `blocking`, `review_required`, or `informational`. Blocking fidelity failures cannot be approved away. Review-required screens show affected pages, extracted source, proposed handling, evidence, and impact, then allow correction, rerun, approval of a non-fidelity-compromising interpretation, or cancellation. Provider routing is preselected by stage. Separately billed fallback approval names the job, stage, provider/model, reason, incremental estimate, projected book total, and applies to one attempt only.

The complete result remains in the private Mac web application: player and M4A, transcript with page references, Transformation Report, validation result, provider provenance, cost, and delivery status. Copy only the M4A to an iCloud Drive output folder; do not build an iPhone application or treat iCloud presence as proof of offline retention. Use in-app status plus optional macOS notifications for review, paid approval, failure, and readiness.

The provisional Learning Plan is measured in Listening Sessions, not calendar days. In the pilot, successful delivery automatically marks that session completed and unlocks—but does not start—the next Episode. In the future Learning System, delivery is insufficient: a typed check-in or quiz must satisfy the Progress Gate before the next Episode can be created. The user confirmed this workflow on 2026-08-17.
