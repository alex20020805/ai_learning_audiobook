# Audio Learning Product

This context describes a personal system that transforms selected source material into trustworthy, downloadable audio for screen-free learning.

## Language

**Source Document**:
A user-supplied technical or nonfiction PDF from which learning material is derived.
_Avoid_: Knowledge base, training data

**Book Workspace**:
A persistent product space anchored to one immutable Source Document edition and its derived structure, plan, Episodes, and progress.
_Avoid_: Upload, job, mutable book file

**Source Chapter**:
The user-selected chapter or comparable section of a Source Document that bounds one transformation request.
_Avoid_: Upload, corpus

**Source Index**:
A persistent structural representation of a Source Document, including detected chapters, sections, paragraphs, visuals, and page references.
_Avoid_: Transcription, arbitrary chunks

**Audio Lesson**:
A source-grounded audio artifact derived from a Source Chapter and intended for offline listening. A long Source Chapter may become several Episodes.
_Avoid_: AI knowledge download, podcast

**Episode**:
One duration-bounded part of an Audio Lesson. It defaults to 15–25 minutes, while its Book workspace may use an approved custom range; source meaning still governs its boundaries.
_Avoid_: Summary, chunk

**Listening Session**:
One planned Episode intended for a single period of learner consumption, without implying a calendar date.
_Avoid_: Generation job, day, playback event

**Document Processing Job**:
A versioned attempt to validate a Source Document and create or update its Source Index and provisional Learning Plan.
_Avoid_: Episode generation, upload

**Episode Generation Job**:
A versioned attempt to produce one Episode from a confirmed source span and duration policy.
_Avoid_: Listening Session, entire chapter run

**Faithful Track**:
An Audio Lesson mode containing no outside explanation. Its initial form narrates source prose verbatim; its target form may lightly adapt prose for listening without omitting substantive content.
_Avoid_: Summary, AI explanation

**Guided Track**:
A future Audio Lesson mode that may add clearly distinguished explanations and examples, potentially informed by the learner's Obsidian memory.
_Avoid_: Faithful narration, silent enrichment

**Transformation Report**:
An audit artifact describing source-boundary decisions, editorial transformations, visual handling, extraction uncertainty, and material that could not be narrated confidently.
_Avoid_: Transcript, summary

**Offline Consumption**:
Playback of a previously generated and downloaded Audio Lesson without a network connection.
_Avoid_: Fully offline system, local generation

**Learning System**:
A future, separate system that uses retrieval and learner state to support retention, potentially interoperating with Obsidian and borrowing principles from Teach.
_Avoid_: Teach skill, audiobook generator

**Learning Plan**:
An ordered program of Listening Sessions derived from a Source Document, initially estimated from coarse structure and refined as source spans are processed.
_Avoid_: File split, cron job, calendar schedule

**Learner Evidence**:
A quiz result, completion check-in, or clarification question that reveals progress or a possible knowledge gap.
_Avoid_: Chat history, user memory

**Progress Gate**:
The requirement that the learner complete a quiz or shorter verbal check-in before generation of the next Episode begins.
_Avoid_: Cron job, rolling buffer

**Learner Memory**:
A durable, selectively retrieved representation of prior Learner Evidence and concept mastery used by the future Guided Track.
_Avoid_: Entire chat history, prompt context

**Hosted Model**:
A proprietary model accessed through a cloud API and evaluated for applicable text-transformation tasks.
_Avoid_: Enterprise model, speech engine

**Local Model**:
An openly available model executed on user-controlled hardware; the pilot candidate is Qwen3.5 9B through llama.cpp.
_Avoid_: Speech engine, offline audio

**Local Orchestrator**:
A trusted process on the user's computer that coordinates extraction, model calls, storage, and Speech Synthesis for the private application.
_Avoid_: Public web backend, browser UI

**Verbal Check-in**:
A short typed recall exercise that may satisfy the Progress Gate when a full quiz is impractical.
_Avoid_: Voice recording, passive confirmation

**Extraction**:
The conversion of PDF text and layout into the Source Index.
_Avoid_: Transcription, synthesis

**Speech Synthesis**:
The conversion of an approved narration script into audio.
_Avoid_: Transcription, extraction
