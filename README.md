# AI Learning Audiobook

Ticket 01 provides a private, local-first browser surface and Local Orchestrator for importing a native-text PDF into an immutable, content-addressed Book Workspace.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn ai_learning_audiobook.runtime:create_runtime_app \
  --factory --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. Set `AI_AUDIOBOOK_DATA_ROOT` to override the ignored default storage at `work/local-orchestrator`.

The Ticket 01 API is:

- `POST /api/book-workspaces/import` with raw `application/pdf` bytes and an optional `x-source-filename` header;
- `GET /api/book-workspaces` for successfully published Book Workspaces;
- `GET /api/runs/{run_id}` for a durable trace manifest and ordered event stream.

Each HTTP request receives its own run ID. Named application functions record bounded inputs and outputs, causal spans, artifact hashes, failures, and terminal status. Binary inputs are represented by type, byte size, and SHA-256; credentials are excluded from traces.

## Verify

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src
.venv/bin/pytest
```

The learner-authorized book fixture belongs under `test-data/private/`, which is ignored by Git. Do not publish or redistribute it.
