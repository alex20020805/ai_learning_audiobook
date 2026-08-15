# Fidelity and listening evaluation

## Decision

Use a **gated, slice-based evaluation**, not one blended score. Extraction,
structure, packing, scripts, visual narration, and speech are scored separately.
A candidate is eligible for routing only if it passes every trust gate on all
three reference-book selections. Preference, latency, privacy, and cost decide
between candidates only after both have passed.

This is a pilot acceptance test, not evidence that a system generalizes to every
technical book. Every newly observed production failure should become another
regression case.

## Why this shape is evidence-based

- PDF display order is not necessarily reading order. Adobe documents that tagged
  PDF supplies logical word order and that inference on untagged PDFs can be less
  satisfactory. The reference PDF is untagged, so visual gold data is required;
  native text alone is not ground truth. [Adobe Acrobat accessibility
  documentation](https://opensource.adobe.com/dc-acrobat-sdk-docs/library/accessibility/index.html)
- A linearized document must preserve a sequence that does not change meaning.
  W3C explicitly calls out multi-column order, tables, and ordered lists as cases
  where sequence matters. [W3C Understanding Meaningful
  Sequence](https://www.w3.org/WAI/WCAG22/Understanding/meaningful-sequence.html)
- Text segmentation should be compared with a reference segmentation. Report
  exact boundary precision/recall and WindowDiff; WindowDiff was designed to
  distinguish false boundaries, missed boundaries, and near misses more fairly
  than the earlier Pk measure. [Pevzner and Hearst,
  2002](https://aclanthology.org/J02-1002.pdf)
- Generic lexical overlap is not enough for adapted prose. Factual-consistency
  research finds that common summarization metrics can miss source conflicts and
  that showing the supporting and conflicting source spans assists human review.
  [Kryscinski et al., 2020](https://aclanthology.org/2020.emnlp-main.750/)
- OpenAI's current evaluation guidance recommends task-specific tests, component
  isolation, automation where possible, human calibration, and pairwise or
  criteria-based judgments rather than vague impressions. It also warns against
  relying only on generic metrics. [OpenAI evaluation best
  practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
  Anthropic likewise recommends specific, measurable, task-relevant,
  multidimensional success criteria. [Anthropic evaluation
  guidance](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)
- Non-text content needs an alternative that serves the equivalent purpose. W3C's
  examples for charts call for the chart type, high-level result, trends, and
  implications rather than a literal recitation of pixels. [WCAG 2.2, Success
  Criterion 1.1.1](https://www.w3.org/TR/WCAG22/#non-text-content)
- ITU-T P.85 Amendment 1 is specifically about audiobook speech output. It calls
  for representative passages of about one minute and evaluates overall
  impression, pleasantness, listening effort, acceptance, pauses, intonation,
  emotion, and word stress. [ITU-T P.85 Amendment
  1](https://www.itu.int/rec/T-REC-P.85-201303-I%21Amd1)
  The five-point absolute-category scale commonly used for subjective speech
  quality runs from bad (1) to excellent (5). [ITU-T
  P.800.2](https://www.itu.int/rec/T-REC-P.800.2/en)
- Speech quality and intelligibility are different. ITU-T P.807 produces a
  percent-correct intelligibility measure from human choices, while P.85 captures
  audiobook experience. The pilot therefore measures exact critical-term
  intelligibility as well as listening quality. [ITU-T
  P.807](https://www.itu.int/rec/T-REC-P.807-201602-I)

The numerical thresholds below are proposed product thresholds, not values
prescribed by those sources.

## Gold evaluation packet

Create the gold packet once from rendered pages. A reviewer reads the page image,
not parser output, and annotates:

1. ordered blocks and their PDF page;
2. heading text and level;
3. paragraphs, list items, tables, figures, equations, code, notes, captions,
   headers, footers, and decorative material;
4. atomic units that must never be split (paragraph, list item, code block,
   equation plus definition, figure plus caption, worked example, note, and the
   premises through conclusion of a short argument);
5. one-source-span support for every substantive claim unit;
6. exact technical terms, symbols, numbers, code identifiers, and pronunciations;
7. all valid episode boundaries in the 15-25 minute window, ranked as
   `preferred`, `acceptable`, or `invalid`.

The creator reviews every gold item against page renders. A second human reviews
all math, code, visuals, headings, and episode boundaries plus a 20% random sample
of prose. Disagreements are reconciled before any model is scored. If only one
human is available, that person repeats the second pass after at least 24 hours;
the limitation is recorded.

### Three selections from *AI Engineering*

PDF page numbers below refer to the 991-page local reference PDF, not printed page
labels. Start and end at the named structural boundary even when it occurs within
a PDF page.

| Slice | Gold span | Extracted size | Stress tested |
| --- | --- | ---: | --- |
| A - prose and hierarchy | PDF pp. 393-409, `Design Your Evaluation Pipeline` through its `Summary` | about 3,389 words / 24 minutes at 140 wpm | headings, paragraphs, numbered steps, lists, notes, a table, cross-page continuity, upper duration boundary |
| B - mathematical notation | PDF p. 240 at `Understanding Language Modeling Metrics` through PDF p. 252 immediately before `Exact Evaluation` | about 2,477 words / 18 minutes | hierarchy, inline symbols, displayed equations, fractions, superscripts, tables, warnings, lower-middle duration |
| C - code and visual narration | PDF p. 252 at `Exact Evaluation` through PDF p. 266, before `Introduction to Embedding` | about 2,870 words / 21 minutes | Python and tests, numbered operations, technical identifiers, Figure 3-5, captions, quotations, mixed content |

These spans intentionally sit near 20 minutes without cutting a logical unit. The
word estimates are triage estimates only; final duration is measured from produced
audio. During inspection, ordinary Poppler layout extraction corrupted part of the
perplexity formula on PDF p. 252 (an ellipsis emerged as a mojibake sequence). This
is a required extraction-warning case even though the PDF contains selectable text.

## Scorecard and gates

### 1. Extraction and Source Index

Normalize only Unicode composition, discretionary line-break hyphens, and
whitespace before calculating text error. Preserve case, punctuation, numbers,
symbols, and code. Report character error rate (CER), block precision/recall,
reading-order errors, object detection, and page attribution.

| Measure | Pilot gate |
| --- | --- |
| Prose CER | <= 0.5% on every slice |
| Substantive block recall and precision | >= 99.5% on every slice |
| Heading precision / recall / F1 | >= 0.98 overall; no missed top- or second-level heading |
| Heading level and document order | 100% correct |
| Page attribution | 100% of blocks and objects on the correct PDF page(s) |
| Figures, tables, equations, code, and notes detected | 100% recall; >= 95% type accuracy |
| Reading-order inversion, duplicate substantive block, or silent omission | zero |
| Critical extraction-warning recall | 100%; every corrupted/ambiguous formula, symbol, code line, or visual blocks synthesis until reviewed |

False warnings are measured separately and should remain below 10% of detected
objects, but a false warning is a usability defect, not a reason to trade away
critical-warning recall.

### 2. Hierarchy-aware episode packing

Evaluate the parser's hierarchy before the packer. For segmentation, report exact
boundary precision, recall, F1, and WindowDiff against the gold structural
boundaries. For each packed Episode, then measure:

| Measure | Pilot gate |
| --- | --- |
| Structural boundary F1 | >= 0.95 per slice |
| WindowDiff | <= 0.05 per slice |
| Cuts through an atomic unit | zero |
| Start/end boundary | both gold `preferred` or `acceptable`; neither `invalid` |
| Actual audio duration | 15:00-25:00, unless the remaining source chapter is shorter and explicitly marked final |
| Duration estimate error | <= 10% versus synthesized duration after voice-rate calibration |
| Boundary coherence | >= 4/5, where 5 is a complete idea with a natural entry and exit; no score below 4 |
| Source progression | exact contiguous coverage, with neither overlap nor gap between successive Episodes |

Duration is subordinate to meaning: an invalid semantic cut never passes merely
because it is closer to 20 minutes.

### 3. Verbatim MVP script

Allowed transformations are limited to removal of identified page furniture,
normalization of broken line wraps/ligatures, explicit source cues, and the
approved audio representation of non-prose objects. Every transformation must
appear in the Transformation Report.

| Measure | Pilot gate |
| --- | --- |
| Substantive claim-unit recall | 100% |
| Unsupported or contradictory substantive claim units | zero |
| Technical terms, numbers, identifiers, and prose words retained | 100%, after the allowed normalization |
| Differences without a Transformation Report entry | zero |
| Correct source-page cue for every non-prose object | 100% |
| Unresolved extraction warning reaching speech synthesis | zero |

A text-similarity score may be logged for debugging, but it cannot pass a script
that fails any gate above.

### 4. Listening-adapted Faithful Track script

Annotate the adapted script into atomic claim units. Each unit must link to one or
more supporting source spans. Label it `entailed`, `contradicted`, or `unsupported`;
independently check every source claim for preservation.

| Measure | Pilot gate |
| --- | --- |
| Source substantive-claim recall | 100% |
| Adapted claim support precision | 100% entailed; zero unsupported or contradicted |
| Technical values, conditions, qualifications, and causal direction | 100% preserved |
| Outside example, definition, or explanation | zero in the Faithful Track |
| Transformation traceability | 100% of reordered, rephrased, expanded-for-speech, or removed text linked to source and reason |
| Standalone listenability | median >= 4/5 for coherence and ease; no dimension below 3 |
| Preference over verbatim | preferred on at least two of three slices and never rejected for lower trust |

The adapted track cannot compensate for a trust failure with a higher style score.

### 5. Figures, tables, equations, and code

First classify each object as `decorative`, `duplicative`, `contributory`, or
`essential`. Decorative objects may be omitted and reported. A duplicative object
gets a brief cue. Contributory and essential objects receive a spoken alternative
that serves the same purpose as the visual.

| Measure | Pilot gate |
| --- | --- |
| Object coverage and classification | 100% of gold objects addressed |
| Spoken identity | type, number/name, and PDF page correct for 100% |
| Purpose and relationships | all gold decision-relevant entities, comparisons, trends, or data relationships present |
| Equation integrity | every material variable, operator, base, exponent, condition, and relation correct |
| Code integrity | purpose, inputs, outputs, control flow, and identifiers needed by the surrounding argument correct |
| Unsupported interpretation or reversed relationship | zero |
| Audio-inadequate object | explicitly says that the visual must be viewed and supplies its page; never invents a reading |

### 6. Hosted-versus-local text models

Run the selected Hosted Model adapter and `qwen3.5-9b-local` on identical gold
inputs, instructions, output schemas, and context. Record exact model/runtime
version, prompt hash, decoding settings, seed where supported, wall time, token
counts, peak memory, and metered cost. Do not compare speech at this stage.

For each slice and each model, collect two independent runs. Both runs must pass
all relevant script and visual gates. An unstable model is not routable even if its
better run wins a preference test. After gates, anonymize outputs, randomize left/
right order, and ask the reviewer for one of `A`, `B`, or `tie` separately for
faithfulness, listening ease, and visual handling. Reverse the order in a later
session. A preference counts only when both presentations agree.

Routing rule:

1. Disqualify any candidate with a trust-gate failure.
2. If only one passes, route the stage to it.
3. If both pass, prefer the candidate with the primary learner's stable pairwise
   preference.
4. If tied, prefer local execution, then lower latency and lower marginal cost.
5. Never silently fall back to paid API usage; ask first.

Report results by slice and failure class. Do not pool the three slices into a
single score that can hide a math or visual failure.

### 7. Hosted-versus-local speech

Speech receives the **same approved script** for both engines; otherwise the test
confounds script quality with voice quality. Match container, sample rate, channel
count, loudness, speaking-rate target, and pronunciation overrides as closely as
possible. Record engine/version, voice, settings, generation time, file size, and
cost.

Use one approximately 60-second excerpt from each slice, consistent with the
P.85 audiobook method, plus one full 15-25 minute Episode for each finalist.
Excerpts must jointly include prose, numbers and acronyms, an equation, code, and
a figure cue.

| Measure | Pilot gate |
| --- | --- |
| Script fidelity from human transcription | word error rate <= 1.0% per excerpt |
| Critical technical terms, values, symbols, and identifiers | zero errors |
| Unintelligible or confidently mispronounced item | zero; pronunciation uncertainty triggers review |
| Overall impression, voice pleasantness, listening effort, pauses, intonation, emotion/prosodic appropriateness, and word stress | primary learner rating >= 4/5 for every excerpt |
| Acceptance for personal 20-minute listening | `yes` on every excerpt and the full Episode |
| Full-Episode hard defect | zero skips, repeats, truncations, clicks, corrupt joins, or level jumps |

With one primary learner these are **owner ratings**, not a mean opinion score.
If the project later claims general voice quality, use multiple listeners and the
formal P.85/P.800 or P.808 procedures rather than relabeling one person's score as
MOS. [ITU-T P.808](https://www.itu.int/rec/T-REC-P.808-202106-I/en)

## Human review protocol

1. **Freeze the packet.** Store page renders, gold blocks, claims, objects,
   boundaries, pronunciation list, scripts, prompts, and hashes. Keep this gold
   packet hidden from generation systems.
2. **Validate components in order.** Extraction must pass before hierarchy;
   hierarchy before packing; packing before scripts; approved scripts before TTS.
   This isolates the origin of each defect.
3. **Run exact checks first.** Compute CER, block and heading scores, boundary
   metrics, duration, claim coverage, page references, and transformation-report
   completeness. Stop downstream evaluation on a critical failure.
4. **Blind text comparison.** Replace provider names with random codes. Randomize
   display order per slice and again on the reversed-order repeat. The reviewer
   sees the rendered source and support links but not runtime identity, price, or
   latency until scoring is locked.
5. **Blind listening comparison.** Loudness-match and randomize one-minute clips.
   Listen once in a quiet setting for detailed defects and once in the intended
   walking/commuting setting for effort and acceptance. Do not reveal the engine
   until ratings are locked.
6. **Endurance pass.** Listen to a finalist's full Episode without reading the
   transcript. Mark timestamp, defect type, severity, and whether the defect made
   the learner stop or consult the page.
7. **Resolve, do not average, trust failures.** A critical failure is fixed and the
   affected slice rerun. Minor style preferences may be summarized by median and
   pairwise preference.
8. **Publish a slice report.** For every run, retain machine metrics, rubric rows,
   reviewer notes, Transformation Report, audio timestamps, model/voice versions,
   latency, cost, and a pass/fail decision. Add every distinct failure to the
   permanent regression set.

## Severity vocabulary

- **Critical:** substantive omission/addition/contradiction; wrong number,
  equation, code behavior, visual relationship, or page cue; invalid atomic cut;
  unresolved warning synthesized; skipped/repeated/truncated audio. Any critical
  defect fails the run.
- **Major:** meaning remains recoverable but requires consulting the source or
  replaying audio; misleading pause or pronunciation; a merely acceptable rather
  than preferred pack boundary. More than one major defect in a slice fails it.
- **Minor:** audible or editorial blemish with no meaning loss and no extra effort.
  Record it; three repeated instances of the same minor class become a major
  regression case.

## Practical acceptance contract

The pilot passes only when all three selections:

1. pass every extraction, indexing, packing, script, visual, and audio trust gate;
2. produce Episodes between 15 and 25 minutes at valid semantic boundaries;
3. download and play offline on the user's iPhone without corruption;
4. earn the primary learner's acceptance after a commute-like listen; and
5. retain a transcript, page references, Transformation Report, metrics, runtime
   identity, cost, and review evidence sufficient to reproduce the decision.

Model and speech routing remain stage-specific. The local candidate does not need
to beat the hosted candidate everywhere; it needs to pass the relevant stage's
quality gates. Conversely, subscription availability or lower price never excuses
a trust failure.
