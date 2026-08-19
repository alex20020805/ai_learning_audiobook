"""HTTP application boundary for the private Local Orchestrator."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import Response

from ai_learning_audiobook.import_service import (
    SourceRejected,
    import_source_document_content,
    list_published_book_workspaces,
)
from ai_learning_audiobook.tracing import TraceRun, current_run, read_trace, traced
from ai_learning_audiobook.web import PRIVATE_APPLICATION_HTML


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
            if key.casefold()
            in {
                "content-type",
                "content-length",
                "x-source-filename",
                "x-source-edition-of",
            }
        }
        with run.activate():
            middleware_span = run.run_id + ":http"
            run.record(
                "function_started",
                function="trace_http_request",
                span_id=middleware_span,
                inputs={"method": request.method, "path": request.url.path},
            )
            try:
                with run.correlate_children(middleware_span):
                    run.record(
                        "request_received",
                        method=request.method,
                        path=request.url.path,
                        headers=safe_headers,
                        body=request_body,
                    )
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
            Presents source selection, explicit prior-edition linkage, status, and structured
            Book Workspace evidence while using the public HTTP boundary for all data.
        Outputs:
            An HTML response containing the self-contained private browser application.
        Failures:
            Does not perform filesystem or provider work and has no expected domain failure.
        """
        return HTMLResponse(PRIVATE_APPLICATION_HTML)

    @app.post("/api/book-workspaces/import")
    @traced
    async def import_source_document(
        request: Request,
        source_bytes: Annotated[bytes, Body(media_type="application/pdf")],
    ) -> JSONResponse:
        """Import native PDF bytes into a persistent Book Workspace.

        Inputs:
            request: HTTP request carrying filename and optional explicit edition lineage.
            source_bytes: Complete raw PDF body supplied by FastAPI's public request parser.
        Functionality:
            Delegates immutable identity, validation, scan, and atomic publication to the
            import service and exposes stable learner-facing rejection errors.
        Outputs:
            A JSON response containing run identity and the Book Workspace representation.
        Failures:
            Converts SourceRejected into HTTP 422 and propagates unexpected storage errors.
        """
        filename = request.headers.get("x-source-filename", "source.pdf")
        edition_of = request.headers.get("x-source-edition-of")
        try:
            outcome = import_source_document_content(
                data_root=data_root,
                source_bytes=source_bytes,
                filename=filename,
                edition_of=edition_of,
            )
        except SourceRejected as error:
            current_run().record("validation_completed", outcome="rejected", error_code=error.code)
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
