"""Durable, redacted run and function tracing for the Local Orchestrator."""

from __future__ import annotations

import contextlib
import functools
import hashlib
import inspect
import json
from collections.abc import Callable, Iterator, Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from starlette.responses import Response

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
_active_run: ContextVar[TraceRun | None] = ContextVar("active_trace_run", default=None)
_active_span_id: ContextVar[str | None] = ContextVar("active_trace_span_id", default=None)
_secret_keys = frozenset(
    {"authorization", "cookie", "password", "secret", "token", "api_key", "api-key"}
)


def _utc_now() -> str:
    """Return a trace timestamp in UTC.

    Inputs:
        None.
    Functionality:
        Reads the system clock and formats a timezone-aware ISO-8601 value.
    Outputs:
        A UTC timestamp string.
    Failures:
        Propagates platform clock failures.
    """
    return datetime.now(UTC).isoformat()


def _string_preview(value: str) -> dict[str, JsonValue]:
    """Represent a large string without copying it wholesale into a trace.

    Inputs:
        value: A string longer than the inline trace threshold.
    Functionality:
        Retains length and hash plus bounded beginning and ending sentence-like previews.
    Outputs:
        A JSON-compatible metadata mapping.
    Failures:
        Does not raise for valid Python strings.
    """
    sentence_parts = [part.strip() for part in value.replace("\n", " ").split(".") if part.strip()]
    beginning = sentence_parts[0][:160] if sentence_parts else value[:160]
    ending = sentence_parts[-1][-160:] if sentence_parts else value[-160:]
    return {
        "type": "str",
        "size": len(value),
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "beginning": beginning,
        "ending": ending,
    }


def trace_value(value: object, *, key: str | None = None, depth: int = 0) -> JsonValue:
    """Convert an arbitrary input or output into bounded, redacted trace data.

    Inputs:
        value: Application value to describe.
        key: Optional field name used to identify configured secret material.
        depth: Current recursion depth, starting at zero.
    Functionality:
        Preserves small JSON values, summarizes binary and large values, redacts secrets,
        and bounds nested traversal so trace serialization cannot explode.
    Outputs:
        A JSON-compatible value safe for durable trace storage.
    Failures:
        Falls back to a type description instead of raising for unsupported values.
    """
    if key is not None and key.casefold() in _secret_keys:
        return {"type": "redacted", "value": "[REDACTED]"}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Response):
        return {
            "type": type(value).__name__,
            "status_code": value.status_code,
            "body": trace_value(value.body, depth=depth + 1),
        }
    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "size": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
        }
    if isinstance(value, str):
        return value if len(value) <= 240 else _string_preview(value)
    if isinstance(value, Path):
        return {"type": "path", "value": str(value)}
    if depth >= 5:
        return {"type": type(value).__name__, "summary": "maximum trace depth reached"}
    if isinstance(value, Mapping):
        return {
            str(item_key): trace_value(item_value, key=str(item_key), depth=depth + 1)
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        if len(value) > 20:
            return {
                "type": type(value).__name__,
                "size": len(value),
                "beginning": [trace_value(item, depth=depth + 1) for item in value[:3]],
                "ending": [trace_value(item, depth=depth + 1) for item in value[-3:]],
            }
        return [trace_value(item, depth=depth + 1) for item in value]
    return {"type": type(value).__name__}


class TraceRun:
    """Durably records one correlated Local Orchestrator HTTP run."""

    def __init__(self, runs_root: Path) -> None:
        """Create a new durable run directory and initial manifest.

        Inputs:
            runs_root: Writable directory containing all run records.
        Functionality:
            Allocates a unique run identifier and initializes its event stream and manifest.
        Outputs:
            None; initializes this TraceRun instance.
        Failures:
            Propagates filesystem errors when durable trace storage cannot be created.
        """
        self.run_id = str(uuid4())
        self.root = runs_root / self.run_id
        self.root.mkdir(parents=True, exist_ok=False)
        self.events_path = self.root / "events.jsonl"
        self.manifest_path = self.root / "manifest.json"
        self._event_count = 0
        self._write_manifest(outcome="running")

    def _write_manifest(self, *, outcome: str) -> None:
        """Atomically persist the current run summary.

        Inputs:
            outcome: Current run outcome such as running, completed, or failed.
        Functionality:
            Writes a replace-safe manifest with run identity, outcome, and event count.
        Outputs:
            None.
        Failures:
            Propagates filesystem or JSON serialization failures.
        """
        manifest = {
            "run_id": self.run_id,
            "outcome": outcome,
            "event_count": self._event_count,
        }
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.manifest_path)

    def record(self, event_type: str, **details: object) -> None:
        """Append one structured event to this run.

        Inputs:
            event_type: Stable event vocabulary identifying what occurred.
            details: Event fields whose values may require bounding or redaction.
        Functionality:
            Adds correlation, sequence, timestamp, parent span, and safe detail values.
        Outputs:
            None.
        Failures:
            Propagates durable-write failures so missing trace evidence is never silent.
        """
        self._event_count += 1
        event: dict[str, JsonValue] = {
            "run_id": self.run_id,
            "sequence": self._event_count,
            "timestamp": _utc_now(),
            "event_type": event_type,
            "parent_span_id": _active_span_id.get(),
        }
        event.update({key: trace_value(value, key=key) for key, value in details.items()})
        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
        self._write_manifest(outcome="running")

    def finish(self, outcome: str) -> None:
        """Finalize the durable run manifest.

        Inputs:
            outcome: Terminal outcome, normally completed or failed.
        Functionality:
            Persists the final outcome after all terminal events have been written.
        Outputs:
            None.
        Failures:
            Propagates durable-write failures.
        """
        self._write_manifest(outcome=outcome)

    @contextlib.contextmanager
    def activate(self) -> Iterator[None]:
        """Make this run available to traced functions in the current context.

        Inputs:
            None.
        Functionality:
            Installs this run in a context-local slot and restores the prior value on exit.
        Outputs:
            A context manager yielding no value.
        Failures:
            Propagates exceptions from the protected application work.
        """
        token = _active_run.set(self)
        try:
            yield
        finally:
            _active_run.reset(token)

    @contextlib.contextmanager
    def correlate_children(self, parent_span_id: str) -> Iterator[None]:
        """Assign a causal parent to nested trace events.

        Inputs:
            parent_span_id: Active function span that owns subsequent nested work.
        Functionality:
            Installs the parent span context for child functions and restores it on exit.
        Outputs:
            A context manager yielding no value.
        Failures:
            Propagates exceptions from the protected application work.
        """
        token = _active_span_id.set(parent_span_id)
        try:
            yield
        finally:
            _active_span_id.reset(token)


def current_run() -> TraceRun:
    """Return the active request's durable trace run.

    Inputs:
        None.
    Functionality:
        Reads context-local trace state established by HTTP middleware.
    Outputs:
        The active TraceRun instance.
    Failures:
        Raises RuntimeError when application work runs outside a trace context.
    """
    run = _active_run.get()
    if run is None:
        raise RuntimeError("No active trace run")
    return run


def record_artifact(path: Path, *, media_type: str, sha256: str) -> None:
    """Record a durable application artifact in the active run.

    Inputs:
        path: Durable artifact location.
        media_type: MIME type or structured artifact media type.
        sha256: Cryptographic digest of the artifact bytes.
    Functionality:
        Appends an artifact event without reading or duplicating its full content.
    Outputs:
        None.
    Failures:
        Raises when no run is active or durable trace storage fails.
    """
    current_run().record("artifact_written", path=path, media_type=media_type, sha256=sha256)


def _record_function_start(function: Callable[..., object], arguments: Mapping[str, object]) -> str:
    """Create a correlated function-start event.

    Inputs:
        function: Application callable about to execute.
        arguments: Bound argument names and values.
    Functionality:
        Allocates a span and records bounded inputs under the current parent span.
    Outputs:
        The new span identifier.
    Failures:
        Raises when no run is active or durable trace storage fails.
    """
    span_id = str(uuid4())
    current_run().record(
        "function_started", function=function.__name__, span_id=span_id, inputs=dict(arguments)
    )
    return span_id


def _record_function_terminal(
    *,
    function: Callable[..., object],
    span_id: str,
    output: object = None,
    error: Exception | None = None,
) -> None:
    """Create a correlated function completion or failure event.

    Inputs:
        function: Application callable that finished.
        span_id: Span identifier allocated at function start.
        output: Returned application value when successful.
        error: Raised exception when unsuccessful.
    Functionality:
        Writes the matching terminal event with bounded output or error metadata.
    Outputs:
        None.
    Failures:
        Raises when no run is active or durable trace storage fails.
    """
    if error is None:
        current_run().record(
            "function_completed", function=function.__name__, span_id=span_id, output=output
        )
    else:
        current_run().record(
            "function_failed",
            function=function.__name__,
            span_id=span_id,
            error_type=type(error).__name__,
            error=str(error),
        )


def traced[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    """Decorate a named application function with bounded input/output tracing.

    Inputs:
        function: Synchronous or asynchronous named application function.
    Functionality:
        Records start and terminal events, propagates parent spans, and preserves the
        original callable's signature and metadata.
    Outputs:
        A callable with the same public type and behavior plus durable trace events.
    Failures:
        Re-raises application failures after recording them; trace-write failures surface.
    """
    signature = inspect.signature(function)

    if inspect.iscoroutinefunction(function):

        @functools.wraps(function)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            """Trace an asynchronous application-function invocation.

            Inputs:
                args: Positional arguments accepted by the decorated function.
                kwargs: Keyword arguments accepted by the decorated function.
            Functionality:
                Records bounded inputs, awaits the application function, and records its
                output or failure while maintaining the causal span relationship.
            Outputs:
                The awaited output produced by the decorated application function.
            Failures:
                Re-raises the decorated function's exception after recording it.
            """
            span_id = _record_function_start(
                function, signature.bind_partial(*args, **kwargs).arguments
            )
            token = _active_span_id.set(span_id)
            try:
                output = await function(*args, **kwargs)
                _record_function_terminal(function=function, span_id=span_id, output=output)
                return output
            except Exception as error:
                _record_function_terminal(function=function, span_id=span_id, error=error)
                raise
            finally:
                _active_span_id.reset(token)

        return cast(Callable[P, R], async_wrapper)

    @functools.wraps(function)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        """Trace a synchronous application-function invocation.

        Inputs:
            args: Positional arguments accepted by the decorated function.
            kwargs: Keyword arguments accepted by the decorated function.
        Functionality:
            Records bounded inputs, invokes the application function, and records its
            output or failure while maintaining the causal span relationship.
        Outputs:
            The output produced by the decorated application function.
        Failures:
            Re-raises the decorated function's exception after recording it.
        """
        span_id = _record_function_start(
            function, signature.bind_partial(*args, **kwargs).arguments
        )
        token = _active_span_id.set(span_id)
        try:
            output = function(*args, **kwargs)
            _record_function_terminal(function=function, span_id=span_id, output=output)
            return output
        except Exception as error:
            _record_function_terminal(function=function, span_id=span_id, error=error)
            raise
        finally:
            _active_span_id.reset(token)

    return cast(Callable[P, R], sync_wrapper)


def read_trace(runs_root: Path, run_id: str) -> dict[str, JsonValue]:
    """Read one durable run manifest and its ordered event stream.

    Inputs:
        runs_root: Directory containing all run records.
        run_id: Exact run identifier to retrieve.
    Functionality:
        Validates identifier shape, loads the manifest, and parses every JSONL event.
    Outputs:
        A JSON-compatible mapping with `manifest` and `events`.
    Failures:
        Raises FileNotFoundError for unknown runs and ValueError for unsafe identifiers.
    """
    if not run_id or any(character not in "0123456789abcdef-" for character in run_id):
        raise ValueError("Invalid run identifier")
    run_root = runs_root / run_id
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    events_path = run_root / "events.jsonl"
    events = (
        [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
        if events_path.exists()
        else []
    )
    return {"manifest": manifest, "events": events}
