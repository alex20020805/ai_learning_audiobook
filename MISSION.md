# Mission: Trustworthy Offline Learning from Technical Books

## Why
Convert difficult chapters from technical and nonfiction books into trustworthy 15–25 minute audio lessons that can be understood while walking or commuting without Wi-Fi, then retained through later review.

## Success looks like
- Select a detected chapter from a PDF, correct its boundaries, and receive faithful audio split into 15–25 minute parts.
- Download the finished lesson to an iPhone and play it without a network connection.
- Verify fidelity through a transcript with page references and a transformation report.
- Later reinforce the material through a separate adaptive learning system connected to Obsidian.
- Eventually turn a whole retained Source Document into a multi-day Learning Plan whose next lesson responds to completed review.
- Compare a hosted proprietary model with the locally available Qwen3.5 9B model for applicable transformation tasks.

## Constraints
- The first product specification covers PDF chapter to faithful offline audio.
- The specification uses three horizons: verbatim MVP, target Faithful Track, and future Guided Track and Learning Plan.
- The first implementation may narrate source prose verbatim; the target faithful experience may lightly rewrite it for listening without omitting substantive content.
- Generation may use paid cloud services, including OpenAI, Anthropic, and speech providers.
- Each finished lesson should target 15–25 minutes.
- The initial content domain is technical and nonfiction books.
- Pilot spending requires confirmation and is capped at US$1 per Episode and US$25 per book unless explicitly overridden.

## Out of scope
- Fully local generation.
- Adaptive quizzes, spaced review, and Obsidian learner-state integration in the first product boundary.
- Automatic daily scheduling in the first implementation; the pilot generates on demand.
- Explanatory additions or outside knowledge in the faithful track.
- Modifying the existing Teach skill as part of the initial product.
