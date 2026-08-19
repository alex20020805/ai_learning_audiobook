"""HTTP application boundary for the private Local Orchestrator."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import Response

from ai_learning_audiobook.import_service import (
    SourceRejected,
    import_source_document_content,
    list_published_book_workspaces,
)
from ai_learning_audiobook.tracing import TraceRun, current_run, read_trace, traced


def create_app(data_root: Path) -> FastAPI:
    """Create the private Local Orchestrator HTTP application.

    Inputs:
        data_root: Writable directory that exclusively contains pilot application data.
    Functionality:
        Configures the loopback-oriented API, durable request tracing, and Book Workspace
        persistence so production and tests cannot share state accidentally.
    Outputs:
        A configured FastAPI application suitable for an ASGI server or test client.
    Failures:
        Raises an operating-system error if the data or run roots cannot be created.
    """
    data_root.mkdir(parents=True, exist_ok=True)
    runs_root = data_root / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="AI Learning Audiobook Local Orchestrator")

    @app.middleware("http")
    async def trace_http_request(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Trace one HTTP request from bounded input through terminal response.

        Inputs:
            request: Incoming Local Orchestrator HTTP request.
            call_next: ASGI callback that invokes the selected downstream route.
        Functionality:
            Creates a durable run, records safe request metadata, propagates correlation,
            records terminal status, and exposes the run identifier as a response header.
        Outputs:
            The downstream HTTP response with an `x-run-id` correlation header.
        Failures:
            Records and re-raises downstream failures after finalizing the run as failed.
        Callback contract:
            `call_next` accepts the original Request and asynchronously returns one Response;
            any exception is recorded and propagated unchanged.
        """
        run = TraceRun(runs_root)
        request_body = await request.body()
        safe_headers = {
            key: value
            for key, value in request.headers.items()
            if key.casefold() in {"content-type", "content-length", "x-source-filename"}
        }
        with run.activate():
            middleware_span = run.run_id + ":http"
            run.record(
                "function_started",
                function="trace_http_request",
                span_id=middleware_span,
                inputs={"method": request.method, "path": request.url.path},
            )
            run.record(
                "request_received",
                method=request.method,
                path=request.url.path,
                headers=safe_headers,
                body=request_body,
            )
            try:
                response = await call_next(request)
                run.record(
                    "request_completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                )
                run.record(
                    "function_completed",
                    function="trace_http_request",
                    span_id=middleware_span,
                    output={"status_code": response.status_code},
                )
                run.finish("completed")
            except Exception as error:
                run.record(
                    "function_failed",
                    function="trace_http_request",
                    span_id=middleware_span,
                    error_type=type(error).__name__,
                    error=str(error),
                )
                run.finish("failed")
                raise
        response.headers["x-run-id"] = run.run_id
        return response

    @app.get("/")
    @traced
    async def show_private_application() -> HTMLResponse:
        """Render the private Ticket 01 Source Document import surface.

        Inputs:
            None.
        Functionality:
            Presents a local file picker, import action, status region, and structured Book
            Workspace result while submitting raw PDF bytes to the public HTTP boundary.
        Outputs:
            An HTML response containing the self-contained private browser application.
        Failures:
            Does not perform filesystem or provider work and has no expected domain failure.
        """
        return HTMLResponse(
            """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Learning Audiobook</title>
  <style>
    :root { color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #f4f0e8; color: #17211c; }
    main { max-width: 760px; margin: 8vh auto; padding: 2rem; }
    section { background: #fffdf8; border: 1px solid #d9d0c2; border-radius: 16px;
      padding: 2rem; box-shadow: 0 18px 50px rgb(51 42 28 / 10%); }
    h1 { font-family: ui-serif, Georgia, serif; font-size: clamp(2rem, 6vw, 3.6rem);
      line-height: 1; margin: 0 0 1rem; }
    p { color: #526057; line-height: 1.6; }
    label { display: block; font-weight: 700; margin: 2rem 0 .5rem; }
    input { display: block; width: 100%; box-sizing: border-box; padding: .9rem;
      border: 1px solid #aeb8b0; border-radius: 10px; background: white; }
    button { margin-top: 1rem; border: 0; border-radius: 999px; padding: .8rem 1.4rem;
      background: #145c43; color: white; font: inherit; font-weight: 700; cursor: pointer; }
    button:disabled { cursor: wait; opacity: .55; }
    #status { min-height: 1.5rem; margin-top: 1rem; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #17211c; color: #dce9df;
      padding: 1rem; border-radius: 10px; min-height: 3rem; }
  </style>
</head>
<body>
  <main>
    <section>
      <h1>Build a trustworthy listening workspace.</h1>
      <p>Select a native-text PDF. The source remains immutable and every import is traced.</p>
      <label for="source-document">Source Document</label>
      <input id="source-document" type="file" accept="application/pdf">
      <button id="import-source-document" type="button">Import Source Document</button>
      <p id="status" role="status" aria-live="polite"></p>
      <pre id="workspace-result" aria-label="Book Workspace result">No workspace imported.</pre>
    </section>
  </main>
  <script>
    const fileInput = document.querySelector("#source-document");
    const importButton = document.querySelector("#import-source-document");
    const status = document.querySelector("#status");
    const result = document.querySelector("#workspace-result");
    importButton.addEventListener("click", async () => {
      const file = fileInput.files[0];
      if (!file) { status.textContent = "Choose a PDF first."; return; }
      importButton.disabled = true;
      status.textContent = "Validating and scanning the Source Document…";
      try {
        const response = await fetch("/api/book-workspaces/import", {
          method: "POST",
          headers: { "content-type": "application/pdf", "x-source-filename": file.name },
          body: file
        });
        const payload = await response.json();
        result.textContent = JSON.stringify(payload, null, 2);
        status.textContent = response.ok
          ? (payload.reopened ? "Existing Book Workspace reopened." : "Book Workspace created.")
          : payload.error.message;
      } catch (error) {
        status.textContent = `Import failed: ${error.message}`;
      } finally {
        importButton.disabled = false;
      }
    });
  </script>
</body>
</html>"""
        )

    @app.post("/api/book-workspaces/import")
    @traced
    async def import_source_document(request: Request) -> JSONResponse:
        """Import native PDF bytes into a persistent Book Workspace.

        Inputs:
            request: HTTP request with an application/pdf body and source filename header.
        Functionality:
            Delegates immutable content identity, validation, structural scan, and atomic
            publication to the import service and exposes stable rejection errors.
        Outputs:
            A JSON response containing run identity and the Book Workspace representation.
        Failures:
            Converts SourceRejected into HTTP 422 and propagates unexpected storage errors.
        """
        source_bytes = await request.body()
        filename = request.headers.get("x-source-filename", "source.pdf")
        try:
            outcome = import_source_document_content(
                data_root=data_root, source_bytes=source_bytes, filename=filename
            )
        except SourceRejected as error:
            return JSONResponse(
                status_code=422,
                content={
                    "run_id": current_run().run_id,
                    "error": {"code": error.code, "message": error.message},
                },
            )
        return JSONResponse(
            status_code=200 if outcome["reopened"] else 201,
            content={"run_id": current_run().run_id, **outcome},
        )

    @app.get("/api/book-workspaces")
    @traced
    async def list_book_workspaces() -> JSONResponse:
        """List every successfully published Book Workspace.

        Inputs:
            None.
        Functionality:
            Reads public workspace records while ignoring uncommitted temporary artifacts.
        Outputs:
            A JSON response containing zero or more Book Workspace representations.
        Failures:
            Propagates filesystem or JSON errors if retained application data is corrupt.
        """
        return JSONResponse(content={"workspaces": list_published_book_workspaces(data_root)})

    @app.get("/api/runs/{run_id}")
    @traced
    async def get_run_trace(run_id: str) -> JSONResponse:
        """Retrieve one durable run manifest and its ordered events.

        Inputs:
            run_id: Exact run identifier returned by a prior HTTP request.
        Functionality:
            Reads the target run without conflating it with this inspection request's run.
        Outputs:
            A JSON response containing the target manifest and event stream.
        Failures:
            Returns HTTP 404 for unknown or invalid run identifiers.
        """
        try:
            trace = read_trace(runs_root, run_id)
        except (FileNotFoundError, ValueError):
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "run_not_found", "message": "Run not found."}},
            )
        return JSONResponse(content=trace)

    return app
