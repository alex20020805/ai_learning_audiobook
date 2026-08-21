# AI Learning Audiobook

Tickets 01–03 provide a private, local-first browser surface and Local Orchestrator for
importing a native-text PDF into an immutable, content-addressed Book Workspace, confirming
a chapter span, creating a provenance-preserving Source Index, and packing a provisional
Learning Plan. A confirmed Listening Session can then run through a retained, versioned,
verbatim Episode Generation Job with deterministic no-network test audio.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn ai_learning_audiobook.runtime:create_runtime_app \
  --factory --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. Set `AI_AUDIOBOOK_DATA_ROOT` to override the ignored default storage at `work/local-orchestrator`.

The implemented API is:

- `POST /api/book-workspaces/import` with raw `application/pdf` bytes and an optional `x-source-filename` header;
- `GET /api/book-workspaces` for successfully published Book Workspaces;
- `GET /api/book-workspaces/{workspace_id}/chapters` for detected chapter boundaries and
  bounded adjacent evidence;
- `POST /api/book-workspaces/{workspace_id}/plans` for confirmed-span extraction and atomic
  Listening Session packing;
- `GET /api/book-workspaces/{workspace_id}/planning` for retained policy and plan history;
- `POST /api/book-workspaces/{workspace_id}/episodes` for the deterministic verbatim pipeline;
- `GET /api/generation-queue` for the single durable FIFO and active-job evidence;
- `GET /api/book-workspaces/{workspace_id}/episodes` for retained ready Episodes;
- `GET /api/book-workspaces/{workspace_id}/episodes/{episode_id}` for complete structured
  script, transcript, Transformation Report, validation, provenance, and cost evidence;
- `GET /api/book-workspaces/{workspace_id}/episodes/{episode_id}/audio` for retained test WAV;
- `GET /api/runs/{run_id}` for a durable trace manifest and ordered event stream.

Each HTTP request receives its own run ID. Named application functions record bounded inputs and outputs, causal spans, artifact hashes, failures, and terminal status. Binary inputs are represented by type, byte size, and SHA-256; credentials are excluded from traces.

## Verify

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
.venv/bin/mypy src scripts
.venv/bin/pytest
```

Run a retained HTTP smoke test against an authorized native-text book without publishing it:

```bash
.venv/bin/python scripts/smoke_plan.py \
  'test-data/private/AI Engineering by Chip Huyen.pdf' work/smoke-plan \
  --start-page 393 --end-page 409
```

The browser's **Retained Book Workspace** selector reopens planning after a reload. Planning
results show bounded hashes and statistics; complete Source Index and Learning Plan artifacts
remain available beneath the configured data root.

The deterministic Episode button is an integration-test route: it copies the approved
normalized source verbatim, renders short 24 kHz tone-marker WAV chunks, assembles them once,
and records zero network/paid use. The tone markers are intentionally not production narration.
Only a complete Episode that passes source coverage, page-reference, audio, provenance, cost,
and trace gates is published as `ready`.

The learner-authorized book fixture belongs under `test-data/private/`, which is ignored by Git. Do not publish or redistribute it.
