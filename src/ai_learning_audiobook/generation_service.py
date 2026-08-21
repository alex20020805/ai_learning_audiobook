"""Durable, deterministic Episode generation behind the Local Orchestrator boundary."""

from __future__ import annotations

import hashlib
import io
import json
import math
import struct
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from ai_learning_audiobook.planning_service import (
    atomic_write_json,
    load_book_workspace,
    stable_json_hash,
)
from ai_learning_audiobook.tracing import current_run, record_artifact, traced

GENERATION_SCHEMA_VERSION = "1"
PROMPT_VERSION = "faithful-verbatim-v1"
PROVIDER_POLICY_VERSION = "deterministic-test-only-v1"
ACTIVE_JOB_STATUSES = {
    "extracting",
    "scripting",
    "synthesizing",
    "assembling",
    "validating",
}
JOB_LIFECYCLE = (
    "draft",
    "awaiting_span_confirmation",
    "queued",
    "extracting",
    "scripting",
    "synthesizing",
    "assembling",
    "validating",
    "ready",
)


class GenerationRejected(Exception):
    """Carry a stable Episode-generation rejection through the HTTP adapter."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Create one learner-visible generation rejection.

        Inputs:
            code: Stable machine-readable rejection code.
            message: Human-readable corrective guidance.
            status_code: HTTP status appropriate for the rejection.
            details: Optional bounded evidence useful to correct the request.
        Functionality:
            Stores a transport-neutral error contract and initializes Exception text.
        Outputs:
            None; initializes this GenerationRejected instance.
        Failures:
            Does not raise for ordinary string, integer, and mapping inputs.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


@traced
def utc_now() -> str:
    """Return a timezone-aware timestamp for retained job evidence.

    Inputs:
        None.
    Functionality:
        Reads the system clock and formats it as an ISO-8601 UTC value.
    Outputs:
        Timestamp string suitable for JSON persistence.
    Failures:
        Propagates platform clock failures.
    """
    return datetime.now(UTC).isoformat()


@traced
def validate_content_id(value: str, *, field: str) -> str:
    """Validate a content-addressed identifier before using it in a filesystem path.

    Inputs:
        value: Candidate lowercase SHA-256 string.
        field: Public field name used in rejection details.
    Functionality:
        Requires exactly 64 lowercase hexadecimal characters to prevent path traversal.
    Outputs:
        The unchanged validated identifier.
    Failures:
        Raises GenerationRejected when the candidate is not a safe content identifier.
    """
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise GenerationRejected(
            f"invalid_{field}", f"{field.replace('_', ' ').title()} is invalid.", status_code=404
        )
    return value


@traced
def load_generation_inputs(
    data_root: Path, workspace_id: str, plan_id: str, session_number: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load and validate immutable inputs for one Episode Generation Job.

    Inputs:
        data_root: Application data root containing published workspaces.
        workspace_id: Exact Source Document hash identity.
        plan_id: Exact immutable confirmed Learning Plan identity.
        session_number: One-based Listening Session selected for generation.
    Functionality:
        Resolves the retained plan, its Source Index, and the requested session while ensuring
        the plan is confirmed and every identifier is path-safe.
    Outputs:
        Tuple of Source Index, Learning Plan, and Listening Session mappings.
    Failures:
        Raises GenerationRejected for missing, unsafe, unconfirmed, or unknown inputs and
        propagates JSON corruption errors from retained artifacts.
    """
    validate_content_id(workspace_id, field="workspace_id")
    validate_content_id(plan_id, field="plan_id")
    try:
        load_book_workspace(data_root, workspace_id)
    except Exception as error:
        raise GenerationRejected(
            "workspace_not_found", "The Book Workspace does not exist.", status_code=404
        ) from error
    workspace_root = data_root / "book-workspaces" / workspace_id
    plan_path = workspace_root / "plans" / f"{plan_id}.json"
    if not plan_path.is_file():
        raise GenerationRejected(
            "plan_not_found", "The Learning Plan does not exist.", status_code=404
        )
    plan = cast(dict[str, Any], json.loads(plan_path.read_text(encoding="utf-8")))
    if plan.get("status") != "confirmed":
        raise GenerationRejected(
            "plan_not_confirmed",
            "Confirm all planning gates before starting generation.",
            status_code=409,
        )
    sessions = cast(list[dict[str, Any]], plan.get("listening_sessions", []))
    session = next(
        (item for item in sessions if int(item.get("session_number", 0)) == session_number), None
    )
    if session is None:
        raise GenerationRejected(
            "session_not_found",
            "Select a Listening Session present in the confirmed plan.",
            status_code=404,
        )
    source_index_id = validate_content_id(
        str(plan.get("source_index_sha256", "")), field="source_index_id"
    )
    source_index_path = workspace_root / "source-indexes" / f"{source_index_id}.json"
    if not source_index_path.is_file():
        raise GenerationRejected(
            "source_index_not_found",
            "The plan's immutable Source Index is unavailable.",
            status_code=409,
        )
    source_index = cast(dict[str, Any], json.loads(source_index_path.read_text(encoding="utf-8")))
    return source_index, plan, session


@traced
def build_job_pins(
    workspace_id: str,
    source_index: dict[str, Any],
    plan: dict[str, Any],
    session: dict[str, Any],
) -> dict[str, Any]:
    """Build the immutable compatibility pins for a Generation Job version.

    Inputs:
        workspace_id: Immutable Source Document identity.
        source_index: Confirmed detailed extraction artifact.
        plan: Confirmed Learning Plan artifact.
        session: Selected ordered Listening Session.
    Functionality:
        Captures source, boundary, duration, prompt, schema, provider-policy, and upstream
        artifact versions so later retry decisions can be reconstructed exactly.
    Outputs:
        JSON-compatible pin mapping with a stable compatibility hash.
    Failures:
        Raises KeyError if required retained artifacts violate their schema.
    """
    pins = {
        "source_document_sha256": workspace_id,
        "source_index_sha256": source_index["sha256"],
        "plan_id": plan["plan_id"],
        "session_number": session["session_number"],
        "session_node_ids_sha256": stable_json_hash(session["node_ids"]),
        "boundary": {
            "start_physical_page": session["start_physical_page"],
            "end_physical_page": session["end_physical_page"],
        },
        "duration_policy_version": plan["duration_policy"]["version"],
        "prompt_version": PROMPT_VERSION,
        "schema_version": GENERATION_SCHEMA_VERSION,
        "provider_policy_version": PROVIDER_POLICY_VERSION,
    }
    pins["compatibility_sha256"] = stable_json_hash(pins)
    return pins


@traced
def validate_session_source_coverage(source_index: dict[str, Any], session: dict[str, Any]) -> None:
    """Reject corrupt session-to-source references before allocating a queue entry.

    Inputs:
        source_index: Immutable extraction artifact selected by the plan.
        session: Planned ordered node identities for one Listening Session.
    Functionality:
        Confirms every planned node exists exactly once in the Source Index and has a non-empty
        normalized spoken representation before any partial Generation Job is created.
    Outputs:
        None when preflight coverage is complete.
    Failures:
        Raises GenerationRejected with the first missing, duplicate, or empty node identity.
    """
    nodes = cast(list[dict[str, Any]], source_index.get("nodes", []))
    node_counts: dict[str, int] = {}
    normalized_text: dict[str, str] = {}
    for node in nodes:
        node_id = str(node.get("node_id", ""))
        node_counts[node_id] = node_counts.get(node_id, 0) + 1
        normalized_text[node_id] = str(node.get("normalized_text", ""))
    for node_id in cast(list[str], session.get("node_ids", [])):
        if node_counts.get(node_id) != 1:
            raise GenerationRejected(
                "source_node_missing_or_duplicated",
                "The session cannot be generated because its Source Index coverage is corrupt.",
                status_code=409,
                details={"node_id": node_id, "occurrences": node_counts.get(node_id, 0)},
            )
        if not normalized_text[node_id].strip():
            raise GenerationRejected(
                "empty_substantive_node",
                "A planned source unit has no faithful spoken representation.",
                status_code=409,
                details={"node_id": node_id},
            )


@traced
def read_generation_queue(data_root: Path) -> dict[str, Any]:
    """Read the one durable FIFO queue shared by all Book Workspaces.

    Inputs:
        data_root: Application data root.
    Functionality:
        Loads retained queue order and job statuses or supplies an empty versioned queue.
    Outputs:
        Queue mapping with ordered entries and active-job summary.
    Failures:
        Propagates JSON and filesystem errors for a corrupt retained queue.
    """
    queue_path = data_root / "generation-queue.json"
    if not queue_path.is_file():
        return {"schema_version": GENERATION_SCHEMA_VERSION, "entries": []}
    return cast(dict[str, Any], json.loads(queue_path.read_text(encoding="utf-8")))


@traced
def queue_view(queue: dict[str, Any]) -> dict[str, Any]:
    """Produce the externally visible bounded view of the durable FIFO queue.

    Inputs:
        queue: Complete retained generation queue mapping.
    Functionality:
        Preserves FIFO order and status history while calculating the sole active job.
    Outputs:
        JSON-compatible queue view with at most one active job identifier.
    Failures:
        Does not raise for a schema-compatible queue mapping.
    """
    entries = cast(list[dict[str, Any]], queue.get("entries", []))
    active = [entry["job_id"] for entry in entries if entry.get("status") in ACTIVE_JOB_STATUSES]
    return {
        "schema_version": queue.get("schema_version", GENERATION_SCHEMA_VERSION),
        "active_job_id": active[0] if active else None,
        "active_job_count": len(active),
        "entries": entries,
    }


@traced
def persist_queue(data_root: Path, queue: dict[str, Any]) -> str:
    """Atomically persist and trace the durable FIFO queue.

    Inputs:
        data_root: Application data root.
        queue: Complete ordered queue state.
    Functionality:
        Writes one replace-safe queue artifact and records its digest in the active run.
    Outputs:
        SHA-256 digest of the exact queue artifact bytes.
    Failures:
        Propagates JSON serialization, filesystem, and trace-write failures.
    """
    queue_path = data_root / "generation-queue.json"
    digest = atomic_write_json(queue_path, queue)
    record_artifact(
        queue_path, media_type="application/vnd.ai-learning.generation-queue+json", sha256=digest
    )
    return digest


@traced
def persist_json_artifact(path: Path, value: object, *, media_type: str) -> dict[str, str]:
    """Write one JSON job artifact and return its portable evidence reference.

    Inputs:
        path: Final path beneath the application data root.
        value: JSON-compatible artifact content.
        media_type: Versioned artifact media type recorded in traces.
    Functionality:
        Atomically writes JSON, records its hash, and builds a relative reference from the
        nearest Book Workspace directory.
    Outputs:
        Mapping containing absolute path text, media type, and SHA-256 digest.
    Failures:
        Propagates serialization, filesystem, and trace persistence errors.
    """
    digest = atomic_write_json(path, value)
    record_artifact(path, media_type=media_type, sha256=digest)
    return {"path": str(path), "media_type": media_type, "sha256": digest}


@traced
def persist_binary_artifact(path: Path, content: bytes, *, media_type: str) -> dict[str, str]:
    """Atomically write one binary job artifact without logging its encoded content.

    Inputs:
        path: Final durable binary artifact path.
        content: Exact bytes to retain.
        media_type: Binary MIME type recorded in the run manifest.
    Functionality:
        Writes through a sibling temporary file, replaces atomically, hashes the bytes, and
        records bounded artifact evidence.
    Outputs:
        Mapping containing path text, media type, and SHA-256 digest.
    Failures:
        Propagates filesystem and trace persistence errors.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    digest = hashlib.sha256(content).hexdigest()
    record_artifact(path, media_type=media_type, sha256=digest)
    return {"path": str(path), "media_type": media_type, "sha256": digest}


@traced
def transition_job(
    data_root: Path,
    queue: dict[str, Any],
    job: dict[str, Any],
    job_path: Path,
    status: str,
) -> None:
    """Durably transition a job and its single shared queue entry together.

    Inputs:
        data_root: Application data root.
        queue: Mutable in-memory durable queue representation.
        job: Mutable Generation Job representation.
        job_path: Durable job artifact path.
        status: Next declared lifecycle state.
    Functionality:
        Validates normal transition order, updates timestamps and history, writes job then
        queue atomically, and emits a reconstructable stage-transition event.
    Outputs:
        None; mutates and persists the supplied job and queue mappings.
    Failures:
        Raises GenerationRejected for an invalid normal transition and propagates write errors.
    """
    current = str(job["status"])
    if status not in JOB_LIFECYCLE:
        raise GenerationRejected("invalid_job_status", f"Unknown job lifecycle status: {status}")
    current_index = JOB_LIFECYCLE.index(current)
    next_index = JOB_LIFECYCLE.index(status)
    if next_index != current_index + 1:
        raise GenerationRejected(
            "invalid_job_transition",
            f"Cannot transition a generation job from {current} to {status}.",
        )
    timestamp = utc_now()
    job["status"] = status
    job["updated_at"] = timestamp
    cast(list[dict[str, str]], job["transitions"]).append(
        {"from": current, "to": status, "at": timestamp, "run_id": current_run().run_id}
    )
    entry = next(
        item
        for item in cast(list[dict[str, Any]], queue["entries"])
        if item["job_id"] == job["job_id"]
    )
    entry["status"] = status
    entry["updated_at"] = timestamp
    persist_json_artifact(
        job_path, job, media_type="application/vnd.ai-learning.generation-job+json"
    )
    persist_queue(data_root, queue)
    current_run().record(
        "job_stage_transition",
        job_id=job["job_id"],
        episode_id=job["episode_id"],
        from_status=current,
        to_status=status,
    )


@traced
def build_verbatim_script(
    source_index: dict[str, Any], session: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Create a source-complete verbatim script and auditable transformations.

    Inputs:
        source_index: Typed provenance-preserving extraction artifact.
        session: Ordered Listening Session containing the exact selected node identities.
    Functionality:
        Copies normalized source text without adding explanation, retains raw/source hashes and
        page references per segment, and records every normalization and non-prose treatment.
    Outputs:
        Tuple of verbatim script, Transformation Report, and Coverage Manifest mappings.
    Failures:
        Raises GenerationRejected if a planned node is missing or has empty substantive text.
    """
    indexed_nodes = {
        str(node["node_id"]): node for node in cast(list[dict[str, Any]], source_index["nodes"])
    }
    segments: list[dict[str, Any]] = []
    transformations: list[dict[str, Any]] = []
    for order, node_id in enumerate(cast(list[str], session["node_ids"])):
        node = indexed_nodes.get(node_id)
        if node is None:
            raise GenerationRejected(
                "source_node_missing",
                "The confirmed session references source material absent from its Source Index.",
                status_code=409,
                details={"node_id": node_id},
            )
        spoken_text = str(node.get("normalized_text", ""))
        if not spoken_text.strip():
            raise GenerationRejected(
                "empty_substantive_node",
                "A planned source unit has no faithful spoken representation.",
                status_code=409,
                details={"node_id": node_id},
            )
        operations = cast(list[dict[str, Any]], node.get("normalization_operations", []))
        for operation in operations:
            transformations.append(
                {
                    "node_id": node_id,
                    "kind": "normalization",
                    "operation": operation,
                    "raw_text_sha256": hashlib.sha256(
                        str(node["raw_text"]).encode("utf-8")
                    ).hexdigest(),
                    "spoken_text_sha256": hashlib.sha256(spoken_text.encode("utf-8")).hexdigest(),
                }
            )
        if node["type"] not in {"heading", "paragraph"}:
            transformations.append(
                {
                    "node_id": node_id,
                    "kind": "non_prose_treatment",
                    "node_type": node["type"],
                    "handling": "retain_normalized_source_text_verbatim",
                }
            )
        segments.append(
            {
                "segment_number": order + 1,
                "node_id": node_id,
                "node_type": node["type"],
                "spoken_text": spoken_text,
                "spoken_text_sha256": hashlib.sha256(spoken_text.encode("utf-8")).hexdigest(),
                "source_node_sha256": node["sha256"],
                "page_references": node["page_references"],
            }
        )
    script = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "mode": "faithful_track_verbatim",
        "prompt_version": PROMPT_VERSION,
        "segments": segments,
        "full_text_sha256": hashlib.sha256(
            "\n\n".join(str(segment["spoken_text"]) for segment in segments).encode("utf-8")
        ).hexdigest(),
    }
    report = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "mode": "faithful_track_verbatim",
        "entries": transformations,
        "outside_explanation_added": False,
        "omitted_node_ids": [],
    }
    coverage = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "expected_node_ids": session["node_ids"],
        "scripted_node_ids": [segment["node_id"] for segment in segments],
        "complete": [segment["node_id"] for segment in segments] == session["node_ids"],
        "source_index_sha256": source_index["sha256"],
    }
    return script, report, coverage


@traced
def render_fake_speech_chunk(text: str, *, identity: str) -> bytes:
    """Render deterministic, network-free 24 kHz mono test speech bytes.

    Inputs:
        text: Exact approved script segment text.
        identity: Stable source node identity used to select a repeatable tone.
    Functionality:
        Encodes a short sine-wave marker whose length varies with word count, enabling audio
        assembly and offset validation without pretending to be intelligible speech or spending.
    Outputs:
        Complete PCM WAV bytes at 24 kHz, mono, signed 16-bit.
    Failures:
        Raises GenerationRejected for empty text and propagates in-memory WAV encoding errors.
    """
    word_count = len(text.split())
    if word_count == 0:
        raise GenerationRejected(
            "empty_speech_input", "Fake speech requires non-empty script text."
        )
    sample_rate = 24_000
    duration_seconds = max(0.08, min(0.4, word_count * 0.01))
    frame_count = int(sample_rate * duration_seconds)
    frequency = 220 + (int(hashlib.sha256(identity.encode("utf-8")).hexdigest()[:4], 16) % 220)
    frames = bytearray()
    for frame_index in range(frame_count):
        envelope = min(1.0, frame_index / 120, (frame_count - frame_index) / 120)
        sample = int(
            5_000 * envelope * math.sin(2 * math.pi * frequency * frame_index / sample_rate)
        )
        frames.extend(struct.pack("<h", sample))
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))
    return output.getvalue()


@traced
def synthesize_fake_speech(script: dict[str, Any]) -> tuple[list[dict[str, Any]], list[bytes]]:
    """Synthesize every approved segment through the deterministic fake speech adapter.

    Inputs:
        script: Valid verbatim script with ordered source-linked segments.
    Functionality:
        Renders one independently hashable 24 kHz WAV chunk per source segment and records
        provider-neutral request/result evidence.
    Outputs:
        Tuple of chunk metadata mappings and corresponding WAV byte payloads.
    Failures:
        Propagates empty-input and in-memory WAV errors from the fake adapter.
    """
    metadata: list[dict[str, Any]] = []
    chunks: list[bytes] = []
    for segment in cast(list[dict[str, Any]], script["segments"]):
        content = render_fake_speech_chunk(
            str(segment["spoken_text"]), identity=str(segment["node_id"])
        )
        chunks.append(content)
        metadata.append(
            {
                "segment_number": segment["segment_number"],
                "node_id": segment["node_id"],
                "input_sha256": segment["spoken_text_sha256"],
                "audio_sha256": hashlib.sha256(content).hexdigest(),
                "byte_size": len(content),
                "sample_rate_hz": 24_000,
            }
        )
    return metadata, chunks


@traced
def assemble_wav_chunks(
    script: dict[str, Any], chunk_metadata: list[dict[str, Any]], chunks: list[bytes]
) -> tuple[bytes, dict[str, Any]]:
    """Assemble deterministic WAV chunks and calculate source-aware transcript offsets.

    Inputs:
        script: Ordered verbatim script artifact.
        chunk_metadata: Provider-neutral evidence for each WAV chunk.
        chunks: Exact WAV byte payloads in matching source order.
    Functionality:
        Validates shared PCM format, concatenates frames once, and maps cumulative audio
        offsets back to each script segment's node and page references.
    Outputs:
        Tuple of assembled WAV bytes and transcript mapping.
    Failures:
        Raises GenerationRejected for count or audio-format mismatches and propagates WAV errors.
    """
    segments = cast(list[dict[str, Any]], script["segments"])
    if not (len(segments) == len(chunk_metadata) == len(chunks)):
        raise GenerationRejected("chunk_count_mismatch", "Speech chunks do not cover the script.")
    frames: list[bytes] = []
    transcript_segments: list[dict[str, Any]] = []
    cumulative_frames = 0
    sample_rate = 24_000
    for segment, metadata, content in zip(segments, chunk_metadata, chunks, strict=True):
        with wave.open(io.BytesIO(content), "rb") as wav:
            if (
                wav.getnchannels() != 1
                or wav.getsampwidth() != 2
                or wav.getframerate() != sample_rate
            ):
                raise GenerationRejected(
                    "incompatible_audio_chunk", "All fake speech chunks must be 24 kHz mono PCM."
                )
            frame_count = wav.getnframes()
            frames.append(wav.readframes(frame_count))
        start_seconds = cumulative_frames / sample_rate
        cumulative_frames += frame_count
        transcript_segments.append(
            {
                "segment_number": segment["segment_number"],
                "node_id": segment["node_id"],
                "page_references": segment["page_references"],
                "spoken_text_sha256": segment["spoken_text_sha256"],
                "audio_chunk_sha256": metadata["audio_sha256"],
                "start_seconds": start_seconds,
                "end_seconds": cumulative_frames / sample_rate,
            }
        )
    output = io.BytesIO()
    with wave.open(output, "wb") as assembled:
        assembled.setnchannels(1)
        assembled.setsampwidth(2)
        assembled.setframerate(sample_rate)
        assembled.writeframes(b"".join(frames))
    transcript = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "sample_rate_hz": sample_rate,
        "duration_seconds": cumulative_frames / sample_rate,
        "segments": transcript_segments,
    }
    return output.getvalue(), transcript


@traced
def validate_ready_episode(
    source_index: dict[str, Any],
    session: dict[str, Any],
    script: dict[str, Any],
    transformation_report: dict[str, Any],
    coverage_manifest: dict[str, Any],
    transcript: dict[str, Any],
    audio: bytes,
    provider_provenance: dict[str, Any],
    cost_record: dict[str, Any],
    trace_manifest_path: Path,
) -> dict[str, Any]:
    """Enforce the complete publication gate for one deterministic Episode.

    Inputs:
        source_index: Immutable extraction artifact used by the selected session.
        session: Planned node sequence and source span.
        script: Candidate verbatim Faithful Track script.
        transformation_report: Recorded normalizations and non-prose treatments.
        coverage_manifest: Expected-versus-scripted node evidence.
        transcript: Candidate source-aware cumulative audio offsets.
        audio: Candidate assembled WAV bytes.
        provider_provenance: Fake adapter identities and request hashes.
        cost_record: Zero-cost deterministic provider record.
        trace_manifest_path: Durable run manifest that correlates this job.
    Functionality:
        Checks exact substantive coverage, absence of outside explanation or omission, complete
        page attribution, valid 24 kHz audio, provider/cost evidence, and trace existence.
    Outputs:
        Versioned validation report whose passed flag is true only when every check succeeds.
    Failures:
        Propagates malformed WAV errors; otherwise reports failed checks without publishing.
    """
    expected_ids = cast(list[str], session["node_ids"])
    source_nodes = {
        str(node["node_id"]): node for node in cast(list[dict[str, Any]], source_index["nodes"])
    }
    script_segments = cast(list[dict[str, Any]], script.get("segments", []))
    transcript_segments = cast(list[dict[str, Any]], transcript.get("segments", []))
    script_ids = [str(segment.get("node_id", "")) for segment in script_segments]
    exact_text = all(
        node_id in source_nodes
        and str(segment.get("spoken_text", "")) == str(source_nodes[node_id]["normalized_text"])
        for node_id, segment in zip(script_ids, script_segments, strict=True)
    )
    with wave.open(io.BytesIO(audio), "rb") as wav:
        audio_valid = (
            wav.getnchannels() == 1
            and wav.getsampwidth() == 2
            and wav.getframerate() == 24_000
            and wav.getnframes() > 0
        )
    checks = {
        "script_complete": script_ids == expected_ids,
        "script_exact_normalized_source": exact_text,
        "coverage_manifest_complete": coverage_manifest.get("complete") is True,
        "outside_explanation_absent": transformation_report.get("outside_explanation_added")
        is False,
        "substantive_omissions_absent": transformation_report.get("omitted_node_ids") == [],
        "transcript_complete": [segment.get("node_id") for segment in transcript_segments]
        == expected_ids,
        "transcript_page_references_complete": all(
            bool(segment.get("page_references")) for segment in transcript_segments
        ),
        "audio_valid_24khz_mono_pcm": audio_valid,
        "provider_provenance_complete": bool(provider_provenance.get("attempts")),
        "cost_record_complete": cost_record.get("total_usd") == 0.0,
        "trace_manifest_present": trace_manifest_path.is_file(),
    }
    return {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "validated_at": utc_now(),
    }


@traced
def relative_artifact_ref(data_root: Path, path: Path) -> str:
    """Convert a durable artifact path into an application-root-relative reference.

    Inputs:
        data_root: Root against which public artifact references are expressed.
        path: Artifact path known to live beneath the root.
    Functionality:
        Resolves both paths and returns a portable POSIX-style relative reference.
    Outputs:
        Relative artifact reference string.
    Failures:
        Raises ValueError when the artifact is outside the application data root.
    """
    return path.resolve().relative_to(data_root.resolve()).as_posix()


@traced
def generate_episode(
    data_root: Path, workspace_id: str, *, plan_id: str, session_number: int
) -> dict[str, Any]:
    """Run one complete deterministic Episode Generation Job to retained readiness.

    Inputs:
        data_root: Application data root.
        workspace_id: Immutable Book Workspace identity.
        plan_id: Confirmed immutable Learning Plan identity.
        session_number: One-based Listening Session selected for generation.
    Functionality:
        Creates an independent pinned job, claims the single FIFO active slot, produces and
        traces verbatim script/audio/evidence artifacts, validates all publication gates, and
        atomically promotes only a complete Episode to ready.
    Outputs:
        Bounded Episode, job, and queue summary mappings for the HTTP adapter.
    Failures:
        Raises GenerationRejected for unsafe inputs, a busy queue, source gaps, or failed
        validation; propagates storage errors without publishing a partial Episode.
    """
    source_index, plan, session = load_generation_inputs(
        data_root, workspace_id, plan_id, session_number
    )
    validate_session_source_coverage(source_index, session)
    queue = read_generation_queue(data_root)
    active_entries = [
        entry
        for entry in cast(list[dict[str, Any]], queue["entries"])
        if entry.get("status") in ACTIVE_JOB_STATUSES
    ]
    if active_entries:
        raise GenerationRejected(
            "generation_queue_busy",
            "Another Episode Generation Job is active; this request was not started.",
            status_code=409,
            details={"active_job_id": active_entries[0]["job_id"]},
        )
    episode_id = stable_json_hash(
        {"workspace_id": workspace_id, "plan_id": plan_id, "session_number": session_number}
    )
    episode_root = data_root / "book-workspaces" / workspace_id / "episodes" / episode_id
    jobs_root = episode_root / "jobs"
    existing_versions = sorted(path for path in jobs_root.glob("*/job.json") if path.is_file())
    job_id = str(uuid4())
    job_root = jobs_root / job_id
    job_path = job_root / "job.json"
    pins = build_job_pins(workspace_id, source_index, plan, session)
    created_at = utc_now()
    job: dict[str, Any] = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "job_id": job_id,
        "episode_id": episode_id,
        "version": len(existing_versions) + 1,
        "workspace_id": workspace_id,
        "status": "draft",
        "created_at": created_at,
        "updated_at": created_at,
        "run_id": current_run().run_id,
        "pins": pins,
        "transitions": [],
        "artifacts": {},
    }
    queue_entry = {
        "sequence": len(cast(list[dict[str, Any]], queue["entries"])) + 1,
        "job_id": job_id,
        "episode_id": episode_id,
        "workspace_id": workspace_id,
        "status": "draft",
        "created_at": created_at,
        "updated_at": created_at,
    }
    cast(list[dict[str, Any]], queue["entries"]).append(queue_entry)
    persist_json_artifact(
        job_path, job, media_type="application/vnd.ai-learning.generation-job+json"
    )
    persist_queue(data_root, queue)
    for status in ("awaiting_span_confirmation", "queued", "extracting", "scripting"):
        transition_job(data_root, queue, job, job_path, status)

    script, transformation_report, coverage_manifest = build_verbatim_script(source_index, session)
    artifact_values = {
        "script": (
            job_root / "script.json",
            script,
            "application/vnd.ai-learning.faithful-script+json",
        ),
        "transformation_report": (
            job_root / "transformation-report.json",
            transformation_report,
            "application/vnd.ai-learning.transformation-report+json",
        ),
        "coverage_manifest": (
            job_root / "coverage-manifest.json",
            coverage_manifest,
            "application/vnd.ai-learning.coverage-manifest+json",
        ),
    }
    for name, (path, value, media_type) in artifact_values.items():
        evidence = persist_json_artifact(path, value, media_type=media_type)
        cast(dict[str, Any], job["artifacts"])[name] = {
            **evidence,
            "artifact_ref": relative_artifact_ref(data_root, path),
        }
    transition_job(data_root, queue, job, job_path, "synthesizing")
    chunk_metadata, chunks = synthesize_fake_speech(script)
    chunk_artifacts: list[dict[str, Any]] = []
    for metadata, content in zip(chunk_metadata, chunks, strict=True):
        chunk_path = job_root / "audio-chunks" / f"{int(metadata['segment_number']):04d}.wav"
        evidence = persist_binary_artifact(chunk_path, content, media_type="audio/wav")
        chunk_artifacts.append(
            {**metadata, **evidence, "artifact_ref": relative_artifact_ref(data_root, chunk_path)}
        )
    chunk_manifest = {"schema_version": GENERATION_SCHEMA_VERSION, "chunks": chunk_artifacts}
    chunk_manifest_path = job_root / "audio-chunks.json"
    chunk_manifest_evidence = persist_json_artifact(
        chunk_manifest_path,
        chunk_manifest,
        media_type="application/vnd.ai-learning.audio-chunks+json",
    )
    cast(dict[str, Any], job["artifacts"])["audio_chunks"] = {
        **chunk_manifest_evidence,
        "artifact_ref": relative_artifact_ref(data_root, chunk_manifest_path),
    }
    transition_job(data_root, queue, job, job_path, "assembling")
    assembled_audio, transcript = assemble_wav_chunks(script, chunk_metadata, chunks)
    audio_path = job_root / "episode.wav"
    transcript_path = job_root / "transcript.json"
    audio_evidence = persist_binary_artifact(audio_path, assembled_audio, media_type="audio/wav")
    transcript_evidence = persist_json_artifact(
        transcript_path,
        transcript,
        media_type="application/vnd.ai-learning.source-transcript+json",
    )
    cast(dict[str, Any], job["artifacts"])["audio"] = {
        **audio_evidence,
        "artifact_ref": relative_artifact_ref(data_root, audio_path),
    }
    cast(dict[str, Any], job["artifacts"])["transcript"] = {
        **transcript_evidence,
        "artifact_ref": relative_artifact_ref(data_root, transcript_path),
    }
    provider_provenance = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "policy_version": PROVIDER_POLICY_VERSION,
        "network_used": False,
        "paid_usage": False,
        "attempts": [
            {
                "stage": "scripting",
                "provider": "deterministic-fake-model",
                "model": "verbatim-copy-v1",
                "input_sha256": source_index["sha256"],
                "output_sha256": script["full_text_sha256"],
            },
            {
                "stage": "synthesizing",
                "provider": "deterministic-fake-speech",
                "model": "tone-marker-v1",
                "sample_rate_hz": 24_000,
                "input_sha256": script["full_text_sha256"],
                "output_sha256": audio_evidence["sha256"],
            },
        ],
    }
    cost_record = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "currency": "USD",
        "total_usd": 0.0,
        "items": [
            {"stage": "scripting", "provider": "deterministic-fake-model", "cost_usd": 0.0},
            {"stage": "synthesizing", "provider": "deterministic-fake-speech", "cost_usd": 0.0},
        ],
    }
    for name, path, value, media_type in (
        (
            "provider_provenance",
            job_root / "provider-provenance.json",
            provider_provenance,
            "application/vnd.ai-learning.provider-provenance+json",
        ),
        (
            "cost_record",
            job_root / "cost.json",
            cost_record,
            "application/vnd.ai-learning.cost+json",
        ),
    ):
        evidence = persist_json_artifact(path, value, media_type=media_type)
        cast(dict[str, Any], job["artifacts"])[name] = {
            **evidence,
            "artifact_ref": relative_artifact_ref(data_root, path),
        }
    transition_job(data_root, queue, job, job_path, "validating")
    trace_manifest_path = data_root / "runs" / current_run().run_id / "manifest.json"
    validation = validate_ready_episode(
        source_index,
        session,
        script,
        transformation_report,
        coverage_manifest,
        transcript,
        assembled_audio,
        provider_provenance,
        cost_record,
        trace_manifest_path,
    )
    validation_path = job_root / "validation.json"
    validation_evidence = persist_json_artifact(
        validation_path,
        validation,
        media_type="application/vnd.ai-learning.validation+json",
    )
    cast(dict[str, Any], job["artifacts"])["validation"] = {
        **validation_evidence,
        "artifact_ref": relative_artifact_ref(data_root, validation_path),
    }
    if not validation["passed"]:
        raise GenerationRejected(
            "episode_validation_failed",
            "Episode evidence is incomplete; no ready result was published.",
            status_code=409,
            details={"checks": validation["checks"]},
        )
    transition_job(data_root, queue, job, job_path, "ready")
    job["completed_at"] = utc_now()
    job["trace_manifest_ref"] = relative_artifact_ref(data_root, trace_manifest_path)
    persist_json_artifact(
        job_path, job, media_type="application/vnd.ai-learning.generation-job+json"
    )
    episode = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "episode_id": episode_id,
        "workspace_id": workspace_id,
        "plan_id": plan_id,
        "session_number": session_number,
        "status": "ready",
        "current_job_id": job_id,
        "current_job_version": job["version"],
        "source_span": {
            "start_physical_page": session["start_physical_page"],
            "end_physical_page": session["end_physical_page"],
        },
        "estimated_listening_minutes": session["estimated_minutes"],
        "generated_test_audio_seconds": transcript["duration_seconds"],
        "script_segment_count": len(cast(list[Any], script["segments"])),
        "artifact_refs": {
            name: evidence["artifact_ref"]
            for name, evidence in cast(dict[str, dict[str, Any]], job["artifacts"]).items()
        },
        "validation": validation,
        "provider_provenance": provider_provenance,
        "cost": cost_record,
        "trace_manifest_ref": job["trace_manifest_ref"],
        "updated_at": job["completed_at"],
    }
    episode_path = episode_root / "episode.json"
    episode_digest = atomic_write_json(episode_path, episode)
    record_artifact(
        episode_path, media_type="application/vnd.ai-learning.episode+json", sha256=episode_digest
    )
    current_run().record(
        "validation_completed",
        outcome="passed",
        job_id=job_id,
        episode_id=episode_id,
        checks=validation["checks"],
    )
    return {"episode": episode, "job": job, "queue": queue_view(queue)}


@traced
def list_retained_episodes(data_root: Path, workspace_id: str) -> list[dict[str, Any]]:
    """List retained ready Episodes for one Book Workspace.

    Inputs:
        data_root: Application data root.
        workspace_id: Exact immutable Book Workspace identity.
    Functionality:
        Validates the workspace and loads only atomically published Episode records in stable
        episode-identity order, ignoring partial job directories.
    Outputs:
        List of complete ready Episode mappings.
    Failures:
        Raises GenerationRejected for unsafe or missing workspaces and propagates JSON errors.
    """
    validate_content_id(workspace_id, field="workspace_id")
    try:
        load_book_workspace(data_root, workspace_id)
    except Exception as error:
        raise GenerationRejected(
            "workspace_not_found", "The Book Workspace does not exist.", status_code=404
        ) from error
    episodes_root = data_root / "book-workspaces" / workspace_id / "episodes"
    return [
        cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(episodes_root.glob("*/episode.json"))
        if path.is_file()
    ]


@traced
def read_retained_episode(data_root: Path, workspace_id: str, episode_id: str) -> dict[str, Any]:
    """Read one complete retained Episode and its current immutable evidence artifacts.

    Inputs:
        data_root: Application data root.
        workspace_id: Exact immutable Book Workspace identity.
        episode_id: Exact content-derived Episode identity.
    Functionality:
        Resolves the published Episode, its current job, and inspectable structured artifacts
        while leaving binary audio represented by a hash and dedicated endpoint.
    Outputs:
        Mapping containing Episode, job, script, transcript, report, validation, provenance,
        cost, and coverage evidence.
    Failures:
        Raises GenerationRejected for unsafe or missing identities and propagates JSON errors.
    """
    validate_content_id(workspace_id, field="workspace_id")
    validate_content_id(episode_id, field="episode_id")
    episode_path = (
        data_root / "book-workspaces" / workspace_id / "episodes" / episode_id / "episode.json"
    )
    if not episode_path.is_file():
        raise GenerationRejected(
            "episode_not_found", "The retained Episode does not exist.", status_code=404
        )
    episode = cast(dict[str, Any], json.loads(episode_path.read_text(encoding="utf-8")))
    job_root = episode_path.parent / "jobs" / str(episode["current_job_id"])
    names = {
        "job": "job.json",
        "script": "script.json",
        "transformation_report": "transformation-report.json",
        "coverage_manifest": "coverage-manifest.json",
        "transcript": "transcript.json",
        "validation": "validation.json",
        "provider_provenance": "provider-provenance.json",
        "cost": "cost.json",
    }
    evidence = {
        name: json.loads((job_root / filename).read_text(encoding="utf-8"))
        for name, filename in names.items()
    }
    return {"episode": episode, **evidence}


@traced
def retained_audio_path(data_root: Path, workspace_id: str, episode_id: str) -> Path:
    """Resolve the published Episode's validated WAV artifact path.

    Inputs:
        data_root: Application data root.
        workspace_id: Exact immutable Book Workspace identity.
        episode_id: Exact content-derived Episode identity.
    Functionality:
        Reads the ready Episode pointer and resolves only its current job's fixed audio name.
    Outputs:
        Existing filesystem path to the retained assembled WAV.
    Failures:
        Raises GenerationRejected for unsafe identities, missing Episodes, or missing audio.
    """
    retained = read_retained_episode(data_root, workspace_id, episode_id)
    episode = cast(dict[str, Any], retained["episode"])
    path = (
        data_root
        / "book-workspaces"
        / workspace_id
        / "episodes"
        / episode_id
        / "jobs"
        / str(episode["current_job_id"])
        / "episode.wav"
    )
    if not path.is_file():
        raise GenerationRejected(
            "episode_audio_missing", "The retained Episode audio is unavailable.", status_code=409
        )
    return path
