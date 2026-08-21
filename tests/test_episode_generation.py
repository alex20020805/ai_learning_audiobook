import json
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from reportlab.pdfgen.canvas import Canvas

from ai_learning_audiobook.app import create_app


def make_generation_pdf(*, page_count: int = 4, words_per_page: int = 240) -> bytes:
    """Create a deterministic native-text chapter suitable for a 5–10-minute Episode.

    Inputs:
        page_count: Positive number of physical PDF pages.
        words_per_page: Number of synthetic substantive words rendered on each page.
    Functionality:
        Renders one outlined chapter with repeated but traceable prose and visible subheadings.
    Outputs:
        Complete in-memory PDF bytes for HTTP-boundary tests.
    Failures:
        Raises ValueError for non-positive sizes and propagates ReportLab encoding errors.
    """
    if page_count < 1 or words_per_page < 1:
        raise ValueError("Generation fixtures require positive page and word counts")
    vocabulary = [
        "faithful",
        "source",
        "evidence",
        "remains",
        "complete",
        "ordered",
        "technical",
        "material",
        "without",
        "omission",
    ]
    output = BytesIO()
    canvas = Canvas(output)
    for page_index in range(page_count):
        if page_index == 0:
            canvas.bookmarkPage("chapter-one")
            canvas.addOutlineEntry("1. Trustworthy Generation", "chapter-one", level=0)
            canvas.setFont("Helvetica-Bold", 16)
            canvas.drawString(54, 760, "1. Trustworthy Generation")
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(54, 738, f"Section {page_index + 1}")
        canvas.setFont("Helvetica", 8)
        remaining = words_per_page
        line_number = 0
        y = 716
        while remaining:
            count = min(10, remaining)
            line = " ".join(
                vocabulary[(line_number * 10 + offset) % len(vocabulary)] for offset in range(count)
            )
            canvas.drawString(54, y, line)
            remaining -= count
            line_number += 1
            y -= 11
        canvas.showPage()
    canvas.save()
    return output.getvalue()


async def create_confirmed_generation_plan(
    client: AsyncClient,
) -> tuple[str, dict[str, object], dict[str, object]]:
    """Import a synthetic source and confirm one generation-ready Listening Session.

    Inputs:
        client: Async client bound to an isolated Local Orchestrator application.
    Functionality:
        Exercises public import and planning endpoints using a valid custom 5–10-minute range.
    Outputs:
        Tuple containing workspace identity, complete Source Index, and confirmed plan mappings.
    Failures:
        Fails the calling test when either public prerequisite endpoint rejects the fixture.
    """
    imported = await client.post(
        "/api/book-workspaces/import",
        content=make_generation_pdf(),
        headers={"content-type": "application/pdf", "x-source-filename": "generation.pdf"},
    )
    assert imported.status_code == 201, imported.text
    workspace_id = str(imported.json()["workspace"]["workspace_id"])
    planned = await client.post(
        f"/api/book-workspaces/{workspace_id}/plans",
        json={
            "heading_index": 0,
            "start_physical_page": 1,
            "end_physical_page": 4,
            "minimum_minutes": 5.0,
            "maximum_minutes": 10.0,
            "allow_cross_chapter": False,
            "approve_short_tail": False,
            "boundary_note": "Synthetic generation fixture.",
        },
    )
    assert planned.status_code == 201, planned.text
    return workspace_id, planned.json()["source_index"], planned.json()["plan"]


@pytest.mark.asyncio
async def test_http_generation_retains_complete_verbatim_ready_episode(tmp_path: Path) -> None:
    """Exercise the complete Ticket 03 path through only public HTTP resources.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Imports, plans, generates, lists, inspects, streams, and traces one deterministic
        Episode while comparing its public script against the public Source Index.
    Outputs:
        None; passes when all ready-state trust artifacts are complete and source-grounded.
    Failures:
        Fails for lifecycle gaps, omissions, outside text, invalid audio, missing evidence,
        network/paid use, incomplete queue state, or broken run correlation.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, source_index, plan = await create_confirmed_generation_plan(client)
        generated = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 1},
        )
        assert generated.status_code == 201, generated.text
        payload = generated.json()
        episode_id = payload["episode"]["episode_id"]
        queue = await client.get("/api/generation-queue")
        episodes = await client.get(f"/api/book-workspaces/{workspace_id}/episodes")
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/episodes/{episode_id}")
        audio = await client.get(f"/api/book-workspaces/{workspace_id}/episodes/{episode_id}/audio")
        trace = await client.get(f"/api/runs/{payload['run_id']}")

    assert payload["episode"]["status"] == "ready"
    assert payload["job"]["version"] == 1
    assert payload["job"]["pins"] == {
        **payload["job"]["pins"],
        "source_document_sha256": workspace_id,
        "source_index_sha256": source_index["sha256"],
        "plan_id": plan["plan_id"],
        "session_number": 1,
        "duration_policy_version": plan["duration_policy"]["version"],
        "prompt_version": "faithful-verbatim-v1",
        "schema_version": "1",
        "provider_policy_version": "deterministic-test-only-v1",
    }
    assert [transition["to"] for transition in payload["job"]["transitions"]] == [
        "awaiting_span_confirmation",
        "queued",
        "extracting",
        "scripting",
        "synthesizing",
        "assembling",
        "validating",
        "ready",
    ]
    assert queue.status_code == 200
    assert queue.json()["queue"]["active_job_count"] == 0
    assert [entry["status"] for entry in queue.json()["queue"]["entries"]] == ["ready"]
    assert episodes.json()["episodes"] == [payload["episode"]]

    evidence = retained.json()
    planned_node_ids = plan["listening_sessions"][0]["node_ids"]
    script_segments = evidence["script"]["segments"]
    source_nodes = {node["node_id"]: node for node in source_index["nodes"]}
    assert [segment["node_id"] for segment in script_segments] == planned_node_ids
    assert all(
        segment["spoken_text"] == source_nodes[segment["node_id"]]["normalized_text"]
        for segment in script_segments
    )
    assert evidence["coverage_manifest"]["complete"] is True
    assert evidence["transformation_report"]["outside_explanation_added"] is False
    assert evidence["transformation_report"]["omitted_node_ids"] == []
    assert [segment["node_id"] for segment in evidence["transcript"]["segments"]] == (
        planned_node_ids
    )
    assert all(segment["page_references"] for segment in evidence["transcript"]["segments"])
    assert evidence["validation"]["passed"] is True
    assert all(evidence["validation"]["checks"].values())
    assert evidence["provider_provenance"]["network_used"] is False
    assert evidence["provider_provenance"]["paid_usage"] is False
    assert evidence["cost"]["total_usd"] == 0.0
    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/wav")
    assert audio.content.startswith(b"RIFF") and b"WAVE" in audio.content[:16]

    assert trace.status_code == 200
    assert trace.json()["manifest"]["outcome"] == "completed"
    events = trace.json()["events"]
    transitions = [event for event in events if event["event_type"] == "job_stage_transition"]
    assert [event["to_status"] for event in transitions] == [
        "awaiting_span_confirmation",
        "queued",
        "extracting",
        "scripting",
        "synthesizing",
        "assembling",
        "validating",
        "ready",
    ]
    assert all(event["job_id"] == payload["job"]["job_id"] for event in transitions)
    assert any(event["event_type"] == "artifact_written" for event in events)
    serialized_trace = json.dumps(trace.json())
    assert "authorization" not in serialized_trace.casefold()
    long_source_node = next(
        node["normalized_text"]
        for node in source_index["nodes"]
        if len(node["normalized_text"]) > 240
    )
    assert serialized_trace.find(long_source_node) == -1

    audio_trace_id = audio.headers["x-run-id"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        audio_trace = await client.get(f"/api/runs/{audio_trace_id}")
    audio_events = audio_trace.json()["events"]
    streamed = [
        event
        for event in audio_events
        if event.get("event_type") == "function_completed"
        and event.get("function") == "get_retained_episode_audio"
    ]
    assert streamed and streamed[0]["output"]["type"] == "FileResponse"
    assert "body" not in streamed[0]["output"]


@pytest.mark.asyncio
async def test_repeated_generation_creates_fifo_job_versions_without_parallel_activity(
    tmp_path: Path,
) -> None:
    """Verify repeated generation is versioned, FIFO ordered, and never multiply active.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Generates the same planned Episode twice and inspects its public queue and current
        retained result after each synchronous job completes.
    Outputs:
        None; passes when job identities differ, versions increase, and queue order is stable.
    Failures:
        Fails if a retry overwrites a job, changes Episode identity, or leaves active work.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, _, plan = await create_confirmed_generation_plan(client)
        request = {"plan_id": plan["plan_id"], "session_number": 1}
        first = await client.post(f"/api/book-workspaces/{workspace_id}/episodes", json=request)
        second = await client.post(f"/api/book-workspaces/{workspace_id}/episodes", json=request)
        queue = await client.get("/api/generation-queue")
        episode_id = second.json()["episode"]["episode_id"]
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/episodes/{episode_id}")

    assert first.status_code == second.status_code == 201
    assert first.json()["episode"]["episode_id"] == second.json()["episode"]["episode_id"]
    assert first.json()["job"]["job_id"] != second.json()["job"]["job_id"]
    assert [first.json()["job"]["version"], second.json()["job"]["version"]] == [1, 2]
    entries = queue.json()["queue"]["entries"]
    assert [entry["sequence"] for entry in entries] == [1, 2]
    assert [entry["status"] for entry in entries] == ["ready", "ready"]
    assert queue.json()["queue"]["active_job_id"] is None
    assert retained.json()["episode"]["current_job_id"] == second.json()["job"]["job_id"]
    assert retained.json()["job"]["version"] == 2


@pytest.mark.asyncio
async def test_generation_rejects_unsafe_or_unknown_inputs_without_queueing(tmp_path: Path) -> None:
    """Challenge path safety, strict typing, unknown sessions, and absent plans.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Sends malformed public requests before any valid generation and inspects durable queue
        state to prove rejected work never receives a FIFO position.
    Outputs:
        None; passes when every request fails safely and the queue remains empty.
    Failures:
        Fails if identifiers traverse paths, booleans coerce to integers, or invalid work queues.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, _, plan = await create_confirmed_generation_plan(client)
        traversal = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": "../planning-state.json", "session_number": 1},
        )
        boolean_number = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": True},
        )
        unknown_session = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 99},
        )
        unknown_plan = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": "0" * 64, "session_number": 1},
        )
        queue = await client.get("/api/generation-queue")

    assert traversal.status_code == 404
    assert traversal.json()["error"]["code"] == "invalid_plan_id"
    assert boolean_number.status_code == 422
    assert unknown_session.status_code == 404
    assert unknown_session.json()["error"]["code"] == "session_not_found"
    assert unknown_plan.status_code == 404
    assert unknown_plan.json()["error"]["code"] == "plan_not_found"
    assert queue.json()["queue"]["entries"] == []


@pytest.mark.asyncio
async def test_corrupt_source_coverage_is_rejected_before_partial_job_publication(
    tmp_path: Path,
) -> None:
    """Verify a missing planned source node cannot strand or publish partial generation.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Corrupts one retained Source Index after planning, calls the public generation endpoint,
        and inspects public queue and Episode collections for any leaked partial state.
    Outputs:
        None; passes when preflight rejects before FIFO allocation or Episode publication.
    Failures:
        Fails if corrupt coverage reaches scripting, remains active, or becomes ready.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, source_index, plan = await create_confirmed_generation_plan(client)
        source_index_path = (
            tmp_path
            / "book-workspaces"
            / workspace_id
            / "source-indexes"
            / f"{source_index['source_index_id']}.json"
        )
        corrupted = json.loads(source_index_path.read_text(encoding="utf-8"))
        corrupted["nodes"] = corrupted["nodes"][1:]
        source_index_path.write_text(json.dumps(corrupted), encoding="utf-8")
        generated = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 1},
        )
        queue = await client.get("/api/generation-queue")
        episodes = await client.get(f"/api/book-workspaces/{workspace_id}/episodes")

    assert generated.status_code == 409
    assert generated.json()["error"]["code"] == "source_node_missing_or_duplicated"
    assert queue.json()["queue"]["entries"] == []
    assert episodes.json()["episodes"] == []
    assert not (tmp_path / "book-workspaces" / workspace_id / "episodes").exists()


@pytest.mark.asyncio
async def test_existing_active_queue_entry_blocks_a_second_generation_job(tmp_path: Path) -> None:
    """Verify a durable active job prevents a second job from entering the FIFO.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Seeds a crash-like active queue entry, requests generation through HTTP, and verifies
        the existing job remains the only visible entry.
    Outputs:
        None; passes when the public response identifies the active job and creates no work.
    Failures:
        Fails if a second job starts, the queue is overwritten, or active count exceeds one.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, _, plan = await create_confirmed_generation_plan(client)
        active_job_id = "existing-active-job"
        queue_path = tmp_path / "generation-queue.json"
        queue_path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "entries": [
                        {
                            "sequence": 1,
                            "job_id": active_job_id,
                            "episode_id": "seeded",
                            "workspace_id": workspace_id,
                            "status": "synthesizing",
                            "created_at": "2026-01-01T00:00:00+00:00",
                            "updated_at": "2026-01-01T00:00:00+00:00",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        generated = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 1},
        )
        queue = await client.get("/api/generation-queue")

    assert generated.status_code == 409
    assert generated.json()["error"]["code"] == "generation_queue_busy"
    assert generated.json()["error"]["details"]["active_job_id"] == active_job_id
    assert queue.json()["queue"]["active_job_count"] == 1
    assert [entry["job_id"] for entry in queue.json()["queue"]["entries"]] == [active_job_id]


@pytest.mark.asyncio
async def test_browser_surface_exposes_generation_queue_and_ready_episode_controls(
    tmp_path: Path,
) -> None:
    """Verify Ticket 03's browser boundary exposes generation and retained-state controls.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Loads the self-contained private application and checks its public HTTP wiring.
    Outputs:
        None; passes when generation, queue, Episode, and audio controls are present.
    Failures:
        Fails when the browser cannot start or inspect the retained deterministic path.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    for control_id in (
        "generation",
        "generate-episode",
        "generation-status",
        "generation-result",
        "queue-result",
        "refresh-episodes",
        "episode-result",
    ):
        assert f'id="{control_id}"' in response.text
    assert "/api/generation-queue" in response.text
    assert "submitEpisodeGeneration" in response.text
    assert "refreshRetainedEpisodes" in response.text
