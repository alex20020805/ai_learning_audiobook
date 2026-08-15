# Hosted and local speech candidates

Research date: 2026-08-15

## Decision

Compare exactly these speech engines in the pilot:

- **Hosted:** OpenAI `gpt-4o-mini-tts-2025-12-15`, using the built-in `marin` voice.
- **Local:** Hexgrad Kokoro-82M v1.0 (`hexgrad/Kokoro-82M`), using American-English `af_heart` through the upstream `kokoro` Python package.

These are **speech renderers only**. Qwen, Codex, or another text model prepares the narration transcript; neither speech engine is allowed to alter, explain, summarize, or plan the lesson. The same frozen transcript, pronunciation dictionary, chunk boundaries, pauses, and final encoding settings must feed both candidates.

OpenAI is the hosted candidate because its documentation calls `gpt-4o-mini-tts` its newest and most reliable TTS model, recommends `marin` or `cedar` for best quality, and exposes direct style instructions plus iPhone-friendly formats. Pinning the available 2025-12-15 snapshot avoids alias drift during evaluation. [OpenAI speech guide](https://developers.openai.com/api/docs/guides/text-to-speech) · [model page](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts)

Kokoro is the local candidate because it is small (82 million parameters; roughly 363 MB in the model repository), Apache-2.0 licensed, has an upstream Apple-Silicon/MPS path, accepts explicit phoneme spelling, and exposes predicted token timing. Its own voice card gives `af_heart` an overall A grade and says voices generally work best around 100–200 tokens, making it a defensible fixed voice and chunk-size starting point. [Kokoro model card](https://huggingface.co/hexgrad/Kokoro-82M) · [voice card](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) · [upstream runtime](https://github.com/hexgrad/kokoro)

## Capability comparison

| Requirement | Hosted: OpenAI | Local: Kokoro |
|---|---|---|
| Input ceiling | The Speech endpoint accepts at most 4,096 characters per request; the model page separately lists 2,000 maximum input tokens. Treat 4,096 characters as the hard API boundary and chunk well below it. [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create) | The model accepts at most 510 phoneme characters per inference unit. The upstream English pipeline performs boundary-aware chunking; the voice card recommends roughly 100–200 tokens and warns of rushing above 400 tokens. [pipeline source](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py) · [voice card](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) |
| Pronunciation control | Free-form `instructions` control accent, intonation, speed, and tone. No SSML, phoneme alphabet, or pronunciation-lexicon field is documented. Technical pronunciations therefore need deterministic transcript preprocessing (for example, expanding abbreviations) plus explicit instructions, and must be tested rather than assumed. [speech guide](https://developers.openai.com/api/docs/guides/text-to-speech) · [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create) | The upstream example supports inline phoneme overrides such as `[Kokoro](/kˈOkəɹO/)`; the pipeline can also generate directly from a phoneme string. This supports a versioned technical-term lexicon. [upstream README](https://github.com/hexgrad/kokoro) · [pipeline source](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py) |
| Timestamps | The Speech endpoint returns audio or streamed audio events; its documented response does not expose word- or phoneme-alignment timestamps. Produce trustworthy section/page timestamps from the application's chunk manifest and measured chunk durations. Word-level subtitles would require a separate forced-alignment pass. [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create) | The upstream pipeline writes `start_ts` and `end_ts` onto English tokens from the model's predicted durations. These are useful draft word timings but are predictions, not forced alignment against the rendered waveform; section/page timestamps should still come from cumulative rendered durations. [pipeline source](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py) |
| Native output | MP3, Opus, AAC, FLAC, WAV, and raw 24 kHz 16-bit PCM; MP3 is the default, and OpenAI recommends WAV or PCM for fastest response. [speech guide](https://developers.openai.com/api/docs/guides/text-to-speech) | The upstream CLI writes mono 24 kHz, 16-bit WAV; the Python API yields audio arrays at 24 kHz. [CLI source](https://github.com/hexgrad/kokoro/blob/main/kokoro/__main__.py) |
| Streaming | HTTP chunked audio is supported, but the pilot does not need playback before a complete offline artifact exists. [speech guide](https://developers.openai.com/api/docs/guides/text-to-speech) | The generator yields one audio result per chunk, which is enough for progress reporting and resumable assembly. [upstream README](https://github.com/hexgrad/kokoro) |
| Current marginal cost | $0.60 per million input text tokens and $12 per million output audio tokens. There is no free tier for this model. The API documentation does not give a deterministic transcript-to-audio-token conversion, so show a preflight estimate, record actual usage, and enforce the approved **$1 per Episode / $25 per book** ceilings. [model pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts) | No per-call or API fee when run on owned hardware; marginal costs are local compute, electricity, and storage. The initial model download is roughly 363 MB. [model repository](https://huggingface.co/hexgrad/Kokoro-82M/tree/main) |
| Licensing and service conditions | This is a hosted service, not an open-weight model. OpenAI's business terms say the customer owns output to the extent permitted by law and remains responsible for rights to input; OpenAI also requires disclosure that the heard voice is AI-generated. API inputs/outputs are not used for training by default, while `/v1/audio/speech` abuse-monitoring logs are retained up to 30 days unless eligible stricter controls apply. [Services Agreement](https://openai.com/policies/services-agreement/) · [speech guide](https://developers.openai.com/api/docs/guides/text-to-speech) · [data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint) | Model weights, `kokoro`, and `misaki` are Apache-2.0. The optional eSpeak-NG fallback used for out-of-dictionary words is GPLv3; personal local use is straightforward, but a later redistributed app must receive a dependency-license review rather than treating the entire runtime as Apache-only. [model license](https://huggingface.co/hexgrad/Kokoro-82M) · [`kokoro` license](https://github.com/hexgrad/kokoro/blob/main/LICENSE) · [`misaki` license](https://github.com/hexgrad/misaki/blob/main/LICENSE) · [eSpeak-NG license](https://github.com/espeak-ng/espeak-ng/blob/master/COPYING) |

## Mac feasibility

The pilot machine is an Apple-Silicon MacBook Pro with an M4 Max and 36 GB RAM. Kokoro's 82M-parameter, roughly 363 MB model is comfortably within that memory budget. The upstream repository explicitly documents M1/M2/M3/M4 acceleration by running with `PYTORCH_ENABLE_MPS_FALLBACK=1`; its pipeline selects PyTorch's `mps` device when available. PyTorch documents MPS as its Metal-backed GPU device for macOS. This establishes **high feasibility**, but it is not a measured throughput result: the comparison ticket must still record cold-start time, real-time factor, peak memory, failures, and thermals on this machine. [Kokoro Mac instructions](https://github.com/hexgrad/kokoro#macos-apple-silicon-gpu-acceleration) · [PyTorch MPS documentation](https://docs.pytorch.org/docs/stable/notes/mps.html)

Installation for the spike should use an isolated Python environment and pinned package/model revisions. English requires `kokoro`, `soundfile`, `misaki[en]`, and optionally eSpeak-NG for out-of-dictionary fallback. After the one-time dependency/model download, synthesis can run without a network connection. Do not bundle or redistribute these dependencies in the MVP without the license review noted above.

## Shared chunking, assembly, and offline delivery contract

1. Freeze the exact transcript before TTS. Apply the same deterministic normalization and technical pronunciation dictionary to both engines; engine-specific phoneme markup belongs in an adapter and must not change displayed transcript text.
2. Split at sentence or paragraph boundaries, preserving source-section and page-reference metadata. Target Kokoro's 100–200-token range and also remain comfortably below OpenAI's 4,096-character request maximum. Never rely on either renderer to ingest a 20-minute Episode in one call.
3. Render every chunk to mono 24 kHz PCM/WAV. Measure the actual duration, reject empty/truncated output, and write a manifest containing transcript span, source pages, engine/model snapshot, voice, pronunciation overrides, duration, checksum, and cumulative offset.
4. Concatenate lossless chunks with a small intentional pause at semantic boundaries, normalize consistently, then encode once to **AAC-LC in an `.m4a` container** for delivery. Keep the WAV master until QA passes. FFmpeg documents concatenation constraints and chapter metadata, and its native AAC encoder; Apple lists M4A, MP3, and WAV among supported AVFoundation file types. [FFmpeg formats](https://ffmpeg.org/ffmpeg-formats.html) · [FFmpeg AAC encoder](https://ffmpeg.org/ffmpeg-codecs.html#aac) · [Apple AV file types](https://developer.apple.com/documentation/avfoundation/avfiletype)
5. Embed Episode title and section chapters where supported, and ship the transcript/transform report as sidecars. The downloadable M4A is a complete local file, so iPhone playback after download does not depend on Wi-Fi. The pilot must verify this manually in iPhone Files because framework support alone does not prove the intended Files-app workflow.

The same assembler removes output-format differences from the listening comparison. It also makes section/page timestamps provider-independent and supports retrying one failed chunk without regenerating the Episode.

## What the comparison still has to decide

The next speech-comparison ticket should render the same three transcript excerpts with these fixed candidates and score:

- technical terms, acronyms, symbols, equations, code, URLs, and citations;
- omissions, repetitions, invented speech, truncation, and silence;
- listening comfort over a continuous 15–25 minute Episode;
- pronunciation-dictionary effort and consistency across chunks;
- cold/warm generation time, real-time factor, memory, reliability, and hosted spend;
- section/page timestamp accuracy after assembly; and
- actual download and offline playback from iPhone Files.

Do not compare Qwen with a hosted text model inside that experiment. Speech quality is the only independent variable. A routing decision can later prefer Kokoro when it passes the quality threshold and ask before spending API credit on the hosted fallback.

## Risks and explicit non-decisions

- `marin` versus `af_heart` is not intended as a voice-persona match; each is the recommended/highest-graded fixed baseline within its engine. The user will judge listenability manually.
- OpenAI has richer prose-style control but lacks a documented exact pronunciation interface or alignment timestamps. Kokoro has stronger explicit phoneme control and timing access, but its upstream voice card itself warns about long-utterance rushing.
- Kokoro's predicted token timestamps must not be represented as verified forced alignment.
- M4A is selected for compact iPhone delivery, not as proof of Books-app audiobook import. The MVP target remains Files download and offline playback.
- Provider/model availability and pricing are time-sensitive; re-check the cited first-party pages when implementation begins.
