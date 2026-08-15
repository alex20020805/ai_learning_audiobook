# Select hosted and local speech candidates

Type: research
Status: resolved
Blocked by: none

## Question

Which single hosted TTS engine and single local speech engine should the pilot compare for technical-book narration? Determine supported input limits, pronunciation controls, timestamps, output formats, audio assembly requirements, current cost, licensing, local hardware feasibility, and reliable offline iPhone playback.

## Answer

Compare OpenAI `gpt-4o-mini-tts-2025-12-15` with the `marin` voice against local Hexgrad Kokoro-82M v1.0 with `af_heart`. Keep transcript generation outside both speech adapters. Render shared sentence/paragraph chunks to 24 kHz WAV, record source-aware cumulative offsets, assemble once, and deliver AAC-LC/M4A for iPhone Files playback. Kokoro is highly feasible on the pilot's M4 Max/36 GB Mac and provides explicit phoneme overrides plus predicted token timings; OpenAI provides richer style instructions and broad output formats but no documented pronunciation lexicon or alignment timestamps. Hosted use must honor the approved $1/Episode and $25/book limits and ask before paid fallback. Full evidence, licensing caveats, and the evaluation handoff are in [the research report](../research/03-hosted-and-local-speech-candidates.md).
