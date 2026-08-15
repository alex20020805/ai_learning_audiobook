# Wayfinder Map: Trustworthy Offline Audio Learning

Label: wayfinder:map

## Destination

A decision-ready three-horizon product specification for a local-first private web application: a verbatim PDF-to-audio MVP, a listening-adapted Faithful Track, and a future progress-aware Guided Track. The specification will make implementation scope, architecture, evaluation, safety, cost, and extension boundaries explicit.

## Notes

- Domain: personal learning from lawfully possessed technical and nonfiction PDFs.
- Every session should consult `MISSION.md`, `CONTEXT.md`, and `NOTES.md`.
- Use Wayfinder for decision sequencing, Domain Modeling for canonical language, Teach for retention principles, Research for primary-source investigations, and Prototype for human-evaluated behavior.
- Planning is the default. Implementation begins only after the decision route is clear.
- Local Markdown tracker: child tickets live in `issues/`; research artifacts live in `research/`.
- Research tickets use isolated `research/<name>` branches and linked worktrees; their reports are merged back as context pointers when resolved.

## Decisions so far

- [Select the native-PDF extraction and indexing strategy](./issues/01-select-native-pdf-extraction-and-indexing-strategy.md) — use pypdf plus pdfplumber/pdfminer to build a provenance-preserving Source Index, with explicit rejection, block, and warning states and model interpretation kept as non-destructive enrichment.
- [Select the local and hosted model runtime strategy](./issues/02-select-local-and-hosted-model-runtime-strategy.md) — route identical structured jobs through loopback llama.cpp or ChatGPT-authenticated `codex exec`; paid API fallback stays disabled until per-job approval.
- [Select hosted and local speech candidates](./issues/03-select-hosted-and-local-speech-candidates.md) — compare pinned OpenAI GPT-4o mini TTS/`marin` with local Kokoro-82M/`af_heart`, assemble shared 24 kHz WAV chunks, and deliver AAC-LC/M4A.
- [Design the fidelity and listening evaluation](./issues/04-design-the-fidelity-and-listening-evaluation.md) — use zero-tolerance trust gates, measurable stage thresholds, three 18–24 minute reference slices, blinded model comparisons, and full-Episode listening endurance.
- [Prototype hierarchy-aware Episode packing](./issues/05-prototype-hierarchy-aware-episode-packing.md) — globally partition ordered atomic SourceNodes into a hard 15–25 minute window targeting 20 minutes, favor semantic and chapter boundaries, cross chapters to prevent short tails, and surface every unverified split for review.

## Not yet specified

- The precise pedagogy, quiz calibration, and mastery-update policy for the Guided Track depend on evidence from the extraction, model, and audio pilots.
- The exact boundary between source-derived explanation and personalized prerequisite bridging depends on the fidelity evaluation.
- Production hardening and provider fallbacks beyond the personal pilot depend on measured reliability and cost.

## Out of scope

- OCR for scanned PDFs in the MVP.
- Video composition, subtitles-as-video, slide generation, and MP4 output.
- Public sharing, commercial audiobook distribution, publisher licensing workflows, and multi-user rights management.
- A native iPhone application or App Store distribution.
- Cloud-hosted or multi-user deployment for the pilot.
- Writing learner state into Obsidian without explicit user instruction.
