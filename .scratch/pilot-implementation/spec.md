# Pilot Implementation: Traceable Native-PDF to Offline Audio

Type: spec
Status: ready-for-agent

## Problem Statement

The learner has a lawfully possessed native-text technical book and wants to turn a selected Source Chapter into trustworthy Episodes for screen-free, offline listening. Today the repository contains the product decisions, extraction research, provider candidates, evaluation rubric, and an accepted Episode-packing prototype, but it does not contain a working private Mac application or Local Orchestrator. The learner therefore cannot yet import a Source Document, correct its detected boundaries, generate a faithful Episode, inspect its evidence, or copy an M4A to iCloud Drive.

Trust is as important as convenience. A plausible-sounding lesson is unacceptable if extraction silently changes reading order, a formula is corrupted, an atomic idea is cut, source material is omitted, outside explanation is introduced into the Faithful Track, or paid API credit is used without approval. The implementation must make every processing decision inspectable and must preserve enough execution evidence to explain what entered and left every application function and every job stage.

## Solution

Build a private, local-first Mac web application backed by a Local Orchestrator. The learner imports an immutable native-text Source Document, reopens or creates its hash-keyed Book Workspace, reviews detected structure and a provisional Learning Plan, confirms the source span and duration policy for the next Episode, and starts an on-demand Episode Generation Job. The system extracts a provenance-preserving Source Index, packs source meaning into a duration-bounded Episode, produces a verbatim Faithful Track script, synthesizes and validates speech, retains the complete result locally, and copies only the finished M4A to an approved iCloud Drive output folder.

The pilot will use the learner's copy of *AI Engineering* by Chip Huyen as the main test Source Document. Automated tests will exercise the product through the Local Orchestrator's public HTTP boundary with deterministic fake provider adapters and isolated temporary Book workspaces. Manual acceptance will use the established three reference selections and the selected real text and speech routes.

Every run will be traceable. A durable run manifest will connect user actions, HTTP requests, Document Processing Jobs, Episode Generation Jobs, application-function calls, artifacts, provider attempts, validations, costs, and delivery. Every named application function will have human-oriented documentation describing its input types and requirements, achieved behavior, output type, failure behavior, and callback contract where applicable. Structured function traces will record inputs and outputs directly when small; large or sensitive values will be represented by type, size, cryptographic hash, durable artifact reference when retained, and bounded beginning/end previews such as first and last complete sentences. Credentials and secrets will never be logged.

## User Stories

1. As a learner, I want to import my native-text PDF, so that I can create an Audio Lesson from a book I lawfully possess.
2. As a learner, I want corrupt, password-blocked, or scan-heavy PDFs to be rejected clearly, so that I do not wait for an unreliable result.
3. As a learner, I want the Source Document identified by its content hash, so that identical bytes reopen the same Book Workspace.
4. As a learner, I want changed PDF bytes treated as a new immutable edition, so that citations and prior Episodes do not silently move.
5. As a learner, I want the original Source Document retained unchanged, so that every derived artifact remains auditable.
6. As a learner, I want a fast structural scan after import, so that I can see detected chapters without waiting for full-book extraction.
7. As a learner, I want detected chapters and sections to retain physical and printed page references, so that I can reconcile the application with the book.
8. As a learner, I want outline evidence and visible-heading evidence exposed when they disagree, so that I can correct uncertain boundaries.
9. As a learner, I want to adjust the selected Source Chapter using adjacent context and first/last-page previews, so that the requested span matches my intent.
10. As a learner, I want detailed extraction limited to confirmed generation spans, so that the pilot avoids unnecessary processing.
11. As a learner, I want the default Episode duration policy to be 15–25 minutes with a 20-minute target, so that listening fits a walk or commute.
12. As a learner, I want to choose an approved custom duration range for a Book Workspace, so that Episodes fit shorter or longer routines.
13. As a learner, I want invalid custom duration bounds rejected before repacking, so that the system cannot create unsupported policies.
14. As a learner, I want duration-policy changes to affect only ungenerated Episodes, so that completed results remain reproducible.
15. As a learner, I want the provisional Learning Plan expressed as ordered Listening Sessions rather than calendar days, so that it describes work without implying a schedule.
16. As a learner, I want Episodes packed at meaningful hierarchy boundaries, so that they begin and end as coherent listening units.
17. As a learner, I want indivisible arguments, examples, code, tables, equations, and figures kept intact, so that duration targets do not damage meaning.
18. As a learner, I want the system to cross a chapter boundary when that is the best faithful way to avoid a short tail, so that the overall plan remains coherent.
19. As a learner, I want a remaining short semantic tail presented with its pages, reason, revised plan length, and cost, so that I can approve it knowingly.
20. As a learner, I want Episodes above 30 minutes blocked for source-structure review, so that a duration exception cannot hide unsafe packing.
21. As a learner, I want every Source Index node to preserve raw and normalized text, hierarchy, geometry, page provenance, evidence, and warnings, so that later outputs can be traced to the PDF.
22. As a learner, I want page furniture excluded from narration but retained as an explicit transformation, so that nothing disappears silently.
23. As a learner, I want code, tables, equations, figures, captions, notes, and callouts represented as typed source nodes, so that non-prose material receives deliberate handling.
24. As a learner, I want unresolved extraction or reading-order failures to block synthesis, so that unreliable source material never becomes confident audio.
25. As a learner, I want review-required warnings to show the affected page, extracted source, evidence, proposed handling, and impact, so that I can make an informed correction.
26. As a learner, I want clean spans to continue automatically after confirmation, so that ordinary generation requires minimal attention.
27. As a learner, I want one visible FIFO queue with at most one active job, so that local resource use and provider attempts remain understandable.
28. As a learner, I want Document Processing Jobs separate from Episode Generation Jobs, so that document indexing and lesson production have independent lifecycles.
29. As a learner, I want each Episode to have an independent versioned Generation Job, so that one failed Episode does not invalidate the entire book.
30. As a learner, I want jobs to retain durable stage checkpoints, so that a compatible retry does not repeat completed work unnecessarily.
31. As a learner, I want a cancellation request to finish the current atomic write without publishing a partial lesson, so that retained state is consistent.
32. As a learner, I want jobs pinned to immutable source, boundary, duration, prompt, and provider-policy versions, so that a result can be reproduced.
33. As a learner, I want obsolete queued jobs marked stale, so that a changed plan cannot silently generate the wrong lesson.
34. As a learner, I want a superseded running job prevented from becoming the current Episode without approval, so that old work cannot replace my newer choice.
35. As a learner, I want the initial Faithful Track script to preserve all substantive source prose, so that listening does not become an unrequested summary.
36. As a learner, I want every allowed normalization or spoken treatment recorded in the Transformation Report, so that I can audit differences from the source.
37. As a learner, I want outside explanations excluded from the Faithful Track, so that source content and model knowledge are never silently mixed.
38. As a learner, I want audio-inadequate visuals to be identified with their page reference, so that the system admits when I need to view the book.
39. As a learner, I want provider routing selected by stage, so that extraction, scripting, and speech can use the route that passed their relevant gates.
40. As a learner, I want a subscription-backed route attempted only where supported, so that existing access can minimize separately billed usage.
41. As a learner, I want separately billed fallback disabled by default, so that a failure cannot spend money automatically.
42. As a learner, I want paid approval to identify the job, stage, provider, model, reason, incremental estimate, and projected book total, so that consent is specific.
43. As a learner, I want paid approval to cover one provider attempt only, so that retries require a fresh cost decision.
44. As a learner, I want the US$1 per Episode and US$25 per book pilot ceilings enforced, so that experimentation remains bounded.
45. As a learner, I want speech generated from the approved script in stable chunks and assembled once, so that long audio remains reliable.
46. As a learner, I want source-aware audio offsets retained, so that an audible defect can be traced back to script and source.
47. As a learner, I want the finished audio delivered as AAC-LC in an M4A container, so that it plays in iPhone Files.
48. As a learner, I want the complete result retained in the Mac application, so that delivery never strips away its evidence.
49. As a learner, I want each result to include audio, transcript with page references, Transformation Report, validation, provenance, cost, and delivery status, so that trust evidence is available in one place.
50. As a learner, I want only the M4A copied to the approved iCloud Drive output folder, so that phone delivery remains simple.
51. As a learner, I want the application to distinguish successful copying from verified offline retention, so that it does not make a false claim about my iPhone.
52. As a learner, I want delivery to complete the current pilot Listening Session and unlock but not start the next Episode, so that generation remains on demand.
53. As a learner, I want in-app status and optional macOS notifications for review, approval, failure, and readiness, so that asynchronous work does not require constant polling.
54. As a learner, I want every orchestrator run assigned a durable identifier, so that I can follow one action across jobs, functions, artifacts, and logs.
55. As a learner, I want every named application function's inputs and outputs traceable, so that unexpected transformations can be localized.
56. As a learner, I want large inputs and outputs represented by their type, size, hash, artifact reference, and bounded beginning/end previews, so that logs stay useful without copying entire book sections into every event.
57. As a learner, I want secret values redacted from traces, so that observability does not expose credentials.
58. As a learner, I want every function documented in human-oriented language, so that future maintainers can understand its contract without reverse-engineering it.
59. As a developer, I want callback contracts documented alongside their callers, so that asynchronous behavior and error propagation are explicit.
60. As a developer, I want structured trace events for function start, function completion, function failure, job-stage transition, artifact creation, provider attempt, validation, and delivery, so that runs can be reconstructed mechanically.
61. As a developer, I want trace correlation to propagate through HTTP requests, queue entries, jobs, function calls, and provider adapters, so that concurrency does not mix evidence from different runs.
62. As a developer, I want deterministic fake model and speech adapters, so that automated tests never require paid credit or nondeterministic provider output.
63. As a developer, I want isolated temporary Book workspaces in automated tests, so that tests cannot mutate the learner's retained library.
64. As a developer, I want black-box tests at the Local Orchestrator HTTP boundary, so that tests assert product behavior rather than internal implementation details.
65. As an evaluator, I want the three accepted *AI Engineering* selections processed with pinned versions and settings, so that extraction, packing, script, and speech evidence is comparable.
66. As an evaluator, I want every distinct critical or major failure retained as a regression case, so that a repaired trust defect does not return unnoticed.
67. As an evaluator, I want real provider comparisons blinded until ratings are locked, so that brand, price, and latency do not bias quality judgments.
68. As a learner, I want the pilot to stop when any zero-tolerance trust gate fails, so that listening quality cannot average away a fidelity defect.

## Implementation Decisions

- The product boundary is a private Mac browser application connected to a Local Orchestrator over loopback. The pilot will not expose a public or multi-user service.
- The Local Orchestrator owns workflow policy, queueing, persistence, trace correlation, provider routing, validation, and artifact publication. The browser UI presents state and submits explicit user decisions; it does not become a second source of workflow truth.
- The Source Document is immutable and keyed by a SHA-256 content digest. An identical import reopens the existing Book Workspace; changed bytes create a new linked edition.
- The learner-authorized copy of *AI Engineering* will be placed in repository-local test-data storage for pilot work. It must not be published, redistributed, or included in a public artifact. Lightweight synthetic fixtures may be committed where redistribution or test speed matters.
- Import has two stages: document preflight plus fast structural scan, followed by detailed extraction only for a confirmed generation span.
- The canonical Source Index is versioned and provenance-preserving. It retains typed nodes, raw and reversibly normalized text, hierarchy, page and geometry references, evidence, warnings, and artifact hashes. Flattened Markdown is not the canonical extraction format.
- Extraction is deterministic-first: pypdf supplies preflight, page labels, and outlines; pdfplumber/pdfminer supplies positioned text, typography, drawings, images, tables, and debugging evidence. Model interpretation may enrich but never overwrite source extraction.
- Warning severity is `blocking`, `review_required`, or `informational`. Fidelity-compromising blocking conditions cannot be approved away.
- Duration policy belongs to the Book Workspace. The default is 15–25 minutes with a 20-minute midpoint. A custom policy must satisfy `5 <= minimum < maximum <= 30` and `5 <= maximum - minimum <= 10`.
- Episode packing operates over accepted atomic Source Index nodes. It favors hierarchy and semantic boundaries, may cross chapter boundaries to prevent short tails, and never silently cuts an indivisible semantic unit.
- Document Processing Jobs and Episode Generation Jobs have separate versioned lifecycles. The pilot runs one active job at a time through a visible durable FIFO queue.
- The normal Episode lifecycle is `draft -> awaiting_span_confirmation -> queued -> extracting -> scripting -> synthesizing -> assembling -> validating -> ready -> delivering -> delivered`. Review, approval, staleness, failure, cancellation, and supersession use the already accepted interruption states.
- Checkpoints are content-addressed and version-compatible. Retry reuses a checkpoint only when its source, policy, prompt, schema, provider configuration, and upstream artifact hashes remain compatible.
- The initial script mode is the verbatim Faithful Track. It permits only recorded page-furniture removal, reversible text normalization, explicit source cues, and approved spoken handling of non-prose objects. It may not add outside explanation or omit substantive content.
- Provider adapters share versioned, validated request and response contracts. The selected hosted text route, local Qwen route, hosted speech route, and local speech route remain stage-specific decisions governed by the pending comparison and architecture tickets.
- Separately billed fallback is disabled until one-attempt approval is recorded. Subscription unavailability pauses the job rather than triggering paid usage.
- Speech is rendered in shared sentence/paragraph chunks to 24 kHz WAV, assembled with source-aware cumulative offsets, and delivered as AAC-LC/M4A.
- The application retains audio, transcript, page references, Transformation Report, validations, provider/runtime provenance, cost, traces, and delivery status. The iCloud Drive delivery copy contains only the M4A.
- Successful pilot delivery completes the current Listening Session and unlocks, but does not start, the next Episode.
- A durable run manifest is the root of traceability. It records run ID, parent action, request correlation, timestamps, software and schema versions, input/output artifact hashes, jobs, provider attempts, approvals, validation results, costs, delivery, and terminal outcome.
- Every named application function emits structured start and terminal trace events. Small values may be recorded directly. Large values use type, logical size, cryptographic hash, durable artifact reference when retained, and bounded first/last complete-sentence previews. Binary values use metadata, hash, and artifact reference rather than console encoding.
- Function tracing must preserve causal parent/child relationships and timing while redacting credentials, authentication material, and other configured secret fields. Trace serialization failures must be visible but must not corrupt domain writes.
- Every named function receives human-oriented documentation covering argument names, input types, validity requirements, behavior, side effects, output type, failure behavior, and any callback invocation/error contract.
- Trace retention and deletion must follow the storage and privacy rules settled by the open storage/Learner Memory decision. Until then, implementation tickets that persist real book content or long-lived traces remain blocked.
- Provider selection, final component boundaries, durable schema, retention rules, and the final pilot acceptance contract will not be invented in this spec. The corresponding unresolved Wayfinder tickets are explicit implementation blockers.

## Testing Decisions

- The primary automated seam is the Local Orchestrator's public loopback HTTP boundary. Tests submit requests and observe HTTP responses, visible resource state, retained artifacts, and structured traces; they do not assert private call order or internal data structures.
- A good automated test describes externally visible behavior: importing an identical Source Document reopens a Book Workspace, a blocking extraction warning prevents synthesis, one-attempt paid approval cannot be reused, cancellation never publishes a partial Episode, or a delivered result contains all promised evidence.
- End-to-end HTTP tests use deterministic fake model and speech adapters, a controlled clock where needed, and isolated temporary Book workspaces. They verify the full path across persistence, queue, extraction, packing, script, audio assembly, validation, and result presentation without network calls or billed usage.
- The user-authorized *AI Engineering* PDF is the main realistic fixture. Tests that do not require its full structure use small synthetic native-text PDFs to stay fast and distributable.
- The three established *AI Engineering* selections form the manual and regression evaluation packet: prose/hierarchy, mathematical notation, and code/visual narration.
- Automated trace tests verify that each request, job transition, application-function call, artifact, provider attempt, approval, validation, and delivery event shares the correct run correlation; that small values are readable; that large values have size/hash/bounded previews; and that configured secrets are absent.
- Documentation checks fail when a named application function lacks the required input, behavior, output, failure, side-effect, or callback-contract description.
- Extraction tests compare rendered pages and gold annotations against Source Index behavior, including reading order, hierarchy, content types, source coverage, page attribution, warning recall, and unresolved-warning blocking.
- Packing tests build on the accepted hierarchy-aware prototype behavior but assert only observable Episode plans: duration bounds, semantic integrity, contiguous coverage, exception presentation, and explicit provisional boundaries.
- Script and visual tests enforce the existing zero-tolerance gates for substantive coverage, unsupported content, technical values, page cues, object handling, and Transformation Report completeness.
- Speech and device acceptance remain human-in-the-loop. Identical approved scripts are compared across the selected hosted and local engines, followed by a full-Episode endurance pass and offline playback check on the learner's iPhone.
- Real-provider tests never run from the ordinary automated suite. They require explicit operator action, pinned provider/runtime configuration, metering, and any required paid approval.
- Existing prior art consists of the accepted hierarchy-aware Episode-packing prototype, the provenance-preserving Source Index contract, and the gated three-slice fidelity/listening rubric. There is no production test harness yet.

## Out of Scope

- OCR or acceptance of scan-heavy Source Documents.
- A listening-adapted Faithful Track in the first implementation slice.
- Guided Track explanations, outside examples, adaptive quizzes, mastery updates, or automatic next-Episode generation.
- Writing learner state to Obsidian or reading Obsidian outside explicitly approved future locations.
- A native or web iPhone application, App Store distribution, or proof that iCloud retained a file offline.
- Public sharing, commercial audiobook distribution, publisher licensing workflows, or multi-user rights management.
- Cloud-hosted deployment, public authentication, production service-level guarantees, or high-availability provider fallback.
- Fully local generation as a product requirement; local candidates are evaluated stage by stage.
- Automatic daily scheduling or a rolling synthesis buffer.
- Replacing the Teach skill or building the future Learning System.
- Treating verbose logs as a substitute for provenance artifacts, validation, or the Transformation Report.
- Logging secrets, duplicating full copyrighted book spans in routine console output, or committing the learner's test PDF to a public repository.

## Further Notes

- This spec synthesizes accepted decisions through the resolved local-first workflow ticket. It does not close or modify the existing Wayfinder decision tickets.
- Implementation remains blocked on the unresolved storage/retention decision, hosted-versus-local text comparison, hosted-versus-local speech comparison, MVP architecture/provider-routing decision, and pilot acceptance contract where those decisions govern a slice.
- The accepted Episode-packing implementation is disposable decision evidence on its prototype branch. Production work may reuse the behavior and tests conceptually but should not assume the prototype is production architecture.
- Pilot spending still requires confirmation and remains capped at US$1 per Episode and US$25 per book unless the learner explicitly overrides it.
- Every new production trust failure should become a permanent regression case with its source evidence, expected warning or rejection behavior, and traced outcome.
