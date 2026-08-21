import json
import math
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from reportlab.pdfgen.canvas import Canvas

from ai_learning_audiobook.app import create_app


def make_planning_pdf(
    *,
    page_count: int = 6,
    words_per_page: int = 360,
    chapter_starts: dict[int, str] | None = None,
    giant_atomic_words: int = 0,
) -> bytes:
    """Create a native-text, outlined PDF for chapter-planning tests.

    Inputs:
        page_count: Positive number of physical pages to render.
        words_per_page: Approximate narratable body words on ordinary pages.
        chapter_starts: Zero-based page indexes mapped to top-level outline titles.
        giant_atomic_words: Optional one-line word count used to create an overlong unit.
    Functionality:
        Renders visible headings, repeatable prose blocks, and top-level outline destinations
        while keeping all fixtures synthetic and deterministic.
    Outputs:
        Complete PDF bytes suitable for the public import API.
    Failures:
        Propagates ReportLab errors and raises for nonsensical negative fixture values.
    """
    if page_count < 1 or words_per_page < 0 or giant_atomic_words < 0:
        raise ValueError("Fixture sizes must be non-negative and include at least one page")
    starts = chapter_starts or {0: "1. Foundations", page_count // 2: "2. Reliability"}
    vocabulary = [
        "traceable",
        "learning",
        "systems",
        "preserve",
        "source",
        "evidence",
        "across",
        "careful",
        "boundaries",
        "reliably",
        "without",
        "omission",
    ]
    output = BytesIO()
    canvas = Canvas(output)
    for page_index in range(page_count):
        heading = starts.get(page_index)
        if heading is not None:
            destination = f"chapter-{page_index}"
            canvas.bookmarkPage(destination)
            canvas.addOutlineEntry(heading, destination, level=0)
            canvas.setFont("Helvetica-Bold", 16)
            canvas.drawString(54, 760, heading)
        canvas.setFont("Helvetica", 8)
        if giant_atomic_words and page_index == 0:
            text = " ".join(
                vocabulary[index % len(vocabulary)] for index in range(giant_atomic_words)
            )
            canvas.drawString(54, 720, text)
        else:
            remaining = words_per_page
            line_number = 0
            y = 728
            while remaining:
                count = min(10, remaining)
                line = " ".join(
                    vocabulary[(line_number * 10 + offset) % len(vocabulary)]
                    for offset in range(count)
                )
                canvas.drawString(54, y, line)
                remaining -= count
                line_number += 1
                y -= 10
                if line_number % 12 == 0:
                    y -= 16
        canvas.showPage()
    canvas.save()
    return output.getvalue()


async def import_planning_workspace(client: AsyncClient, pdf: bytes) -> str:
    """Import a planning fixture and return its workspace identity.

    Inputs:
        client: Async HTTP client bound to an isolated Local Orchestrator.
        pdf: Complete synthetic native-text PDF bytes.
    Functionality:
        Calls the public import endpoint and asserts successful publication.
    Outputs:
        Hash-keyed Book Workspace identifier.
    Failures:
        Fails the calling test if import does not return HTTP 201.
    """
    response = await client.post(
        "/api/book-workspaces/import",
        content=pdf,
        headers={"content-type": "application/pdf", "x-source-filename": "planning.pdf"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["workspace"]["workspace_id"])


def valid_plan_request(**overrides: object) -> dict[str, object]:
    """Build one strict, valid custom-duration planning request.

    Inputs:
        overrides: Request fields that should replace deterministic defaults.
    Functionality:
        Produces a compact baseline request for HTTP-boundary test variations.
    Outputs:
        JSON-compatible request mapping.
    Failures:
        Does not raise for arbitrary override keys; the HTTP API validates them.
    """
    request: dict[str, object] = {
        "heading_index": 0,
        "start_physical_page": 1,
        "end_physical_page": 3,
        "minimum_minutes": 5.0,
        "maximum_minutes": 10.0,
        "allow_cross_chapter": False,
        "approve_short_tail": False,
        "boundary_note": "Checked against adjacent page previews.",
    }
    request.update(overrides)
    return request


@pytest.mark.asyncio
async def test_chapter_inspection_and_confirmed_span_produce_traceable_plan(
    tmp_path: Path,
) -> None:
    """Verify chapter evidence, scoped extraction, typed nodes, and coherent packing.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Imports a two-chapter PDF, inspects its boundaries, confirms only chapter one, and
        examines Source Index and Learning Plan behavior through HTTP.
    Outputs:
        None; passes when every observable Ticket 02 artifact satisfies its contract.
    Failures:
        Fails for missing adjacent evidence, out-of-span extraction, unsafe cuts, or bad hashes.
    """
    app = create_app(tmp_path)
    pdf = make_planning_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, pdf)
        catalog_response = await client.get(f"/api/book-workspaces/{workspace_id}/chapters")
        planned = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans", json=valid_plan_request()
        )
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/planning")

    assert catalog_response.status_code == 200
    chapters = catalog_response.json()["chapters"]
    assert [chapter["title"] for chapter in chapters] == ["1. Foundations", "2. Reliability"]
    assert chapters[0]["suggested_span"] == {
        "start_physical_page": 1,
        "end_physical_page": 3,
        "start_printed_page": "1",
        "end_printed_page": "3",
    }
    assert chapters[0]["previous_heading"] is None
    assert chapters[0]["next_heading"]["title"] == "2. Reliability"
    assert "Foundations" in chapters[0]["first_page_preview"]["beginning"]
    assert chapters[0]["last_page_preview"]["sha256"]

    assert planned.status_code == 201, planned.text
    payload = planned.json()
    source_index = payload["source_index"]
    assert source_index["span"] == {"start_physical_page": 1, "end_physical_page": 3}
    assert {
        reference["physical_page_number"]
        for node in source_index["nodes"]
        for reference in node["page_references"]
    } == {1, 2, 3}
    assert {node["type"] for node in source_index["nodes"]} >= {"heading", "paragraph"}
    assert all(node["atomic"] is True for node in source_index["nodes"])
    assert all(node["raw_text"] and node["normalized_text"] for node in source_index["nodes"])
    assert all(node["hierarchy_path"][0] == "1. Foundations" for node in source_index["nodes"])
    assert all(node["geometry"]["x1"] >= node["geometry"]["x0"] for node in source_index["nodes"])
    assert all(
        node["evidence"]["method"] == "pdfplumber_positioned_words"
        for node in source_index["nodes"]
    )
    assert all(len(node["sha256"]) == 64 for node in source_index["nodes"])
    assert len(source_index["sha256"]) == 64

    plan = payload["plan"]
    assert plan["status"] == "confirmed"
    assert plan["duration_policy"]["target_minutes"] == 7.5
    assert plan["selection"]["boundary_note"] == "Checked against adjacent page previews."
    assert all(session["cuts_atomic_unit"] is False for session in plan["listening_sessions"])
    flattened = [
        node_id for session in plan["listening_sessions"] for node_id in session["node_ids"]
    ]
    assert flattened == [node["node_id"] for node in source_index["nodes"]]
    assert retained.status_code == 200
    assert retained.json()["state"]["latest_plan_id"] == plan["plan_id"]


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(4.0, 10.0), (10.0, 10.0), (10.0, 21.0), (20.0, 31.0), (math.nan, 20.0)],
)
@pytest.mark.asyncio
async def test_invalid_duration_policies_are_rejected_before_repacking(
    tmp_path: Path, minimum: float, maximum: float
) -> None:
    """Verify every policy invariant, including non-finite out-of-box input.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
        minimum: Candidate lower duration bound.
        maximum: Candidate upper duration bound.
    Functionality:
        Submits one invalid policy and checks that no planning state is published.
    Outputs:
        None; passes when invalid policy values fail before extraction/packing persistence.
    Failures:
        Fails when unsupported bounds are coerced, accepted, or partially retained.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, make_planning_pdf())
        planned = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            content=json.dumps(
                valid_plan_request(minimum_minutes=minimum, maximum_minutes=maximum)
            ),
            headers={"content-type": "application/json"},
        )
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/planning")

    assert planned.status_code == 422
    assert planned.json()["error"]["code"] == "invalid_duration_policy"
    assert retained.status_code == 404
    assert not (tmp_path / "book-workspaces" / workspace_id / "source-indexes").exists()


@pytest.mark.asyncio
async def test_duration_changes_create_new_plans_without_mutating_prior_versions(
    tmp_path: Path,
) -> None:
    """Verify workspace policy updates affect only newly planned, ungenerated sessions.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Confirms the same span under two valid policies and reads immutable plan history.
    Outputs:
        None; passes when both versions remain distinct and the state points to the latest.
    Failures:
        Fails when a policy update overwrites the earlier plan or loses its version.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, make_planning_pdf())
        first = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans", json=valid_plan_request()
        )
        second = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json=valid_plan_request(minimum_minutes=6.0, maximum_minutes=12.0),
        )
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/planning")

    assert first.status_code == second.status_code == 201
    assert first.json()["plan"]["plan_id"] != second.json()["plan"]["plan_id"]
    plans = retained.json()["plans"]
    assert len(plans) == 2
    assert plans[0]["duration_policy"]["minimum_minutes"] == 5.0
    assert plans[1]["duration_policy"]["minimum_minutes"] == 6.0
    assert retained.json()["state"]["latest_plan_id"] == plans[1]["plan_id"]


@pytest.mark.asyncio
async def test_adjusted_subsection_start_inside_selected_chapter_is_allowed(tmp_path: Path) -> None:
    """Regress the real-book case where a selection starts after its chapter heading.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Selects the first detected chapter but confirms only its second and third pages.
    Outputs:
        None; passes when overlap is accepted and extraction excludes the heading page.
    Failures:
        Fails when the system requires the original chapter heading page or extracts page one.
    """
    app = create_app(tmp_path)
    pdf = make_planning_pdf(words_per_page=420)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, pdf)
        planned = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json=valid_plan_request(start_physical_page=2, end_physical_page=3),
        )

    assert planned.status_code == 201
    assert planned.json()["source_index"]["span"] == {
        "start_physical_page": 2,
        "end_physical_page": 3,
    }
    assert {
        reference["physical_page_number"]
        for node in planned.json()["source_index"]["nodes"]
        for reference in node["page_references"]
    } == {2, 3}


@pytest.mark.asyncio
async def test_default_policy_and_explicit_chapter_crossing_produce_contiguous_sessions(
    tmp_path: Path,
) -> None:
    """Verify the default midpoint and an explicitly crossed chapter boundary.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Plans a full twenty-minute-scale chapter with defaults, then deliberately crosses a
        detected chapter boundary under a custom policy and compares source continuity.
    Outputs:
        None; passes when defaults target twenty minutes and crossing remains explicit.
    Failures:
        Fails when default bounds drift, crossing is ignored, or source nodes overlap/gap.
    """
    app = create_app(tmp_path)
    full_pdf = make_planning_pdf(
        page_count=9, words_per_page=360, chapter_starts={0: "1. Full Chapter"}
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, full_pdf)
        default_plan = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json={
                "heading_index": 0,
                "start_physical_page": 1,
                "end_physical_page": 9,
            },
        )

        crossed_workspace = await import_planning_workspace(client, make_planning_pdf())
        crossed = await client.post(
            f"/api/book-workspaces/{crossed_workspace}/plans",
            json=valid_plan_request(end_physical_page=4, allow_cross_chapter=True),
        )

    assert default_plan.status_code == 201
    default_policy = default_plan.json()["plan"]["duration_policy"]
    assert default_policy["minimum_minutes"] == 15.0
    assert default_policy["maximum_minutes"] == 25.0
    assert default_policy["target_minutes"] == 20.0
    assert all(
        15 <= session["estimated_minutes"] <= 25
        for session in default_plan.json()["plan"]["listening_sessions"]
    )
    assert crossed.status_code == 201
    assert crossed.json()["plan"]["selection"]["allow_cross_chapter"] is True
    assert crossed.json()["source_index"]["span"]["end_physical_page"] == 4
    crossed_ids = [
        node_id
        for session in crossed.json()["plan"]["listening_sessions"]
        for node_id in session["node_ids"]
    ]
    assert crossed_ids == [node["node_id"] for node in crossed.json()["source_index"]["nodes"]]


@pytest.mark.asyncio
async def test_short_tail_requires_visible_exact_approval_and_is_idempotent(
    tmp_path: Path,
) -> None:
    """Verify a short semantic tail cannot silently become a confirmed session.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Plans a sub-five-minute chapter, inspects the approval packet, approves it, then
        repeats the exact request to probe duplicate-action behavior.
    Outputs:
        None; passes when approval is explicit, versioned, and idempotently retained.
    Failures:
        Fails when the tail is hidden, auto-approved, changes identity, or duplicates history.
    """
    app = create_app(tmp_path)
    pdf = make_planning_pdf(page_count=1, words_per_page=360, chapter_starts={0: "1. Short"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, pdf)
        request = valid_plan_request(end_physical_page=1)
        preview = await client.post(f"/api/book-workspaces/{workspace_id}/plans", json=request)
        approved_request = {**request, "approve_short_tail": True}
        approved = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans", json=approved_request
        )
        repeated = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans", json=approved_request
        )
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/planning")

    assert preview.status_code == 409
    preview_plan = preview.json()["plan"]
    assert preview_plan["status"] == "awaiting_short_tail_approval"
    assert preview_plan["short_tail_approval"] == {
        "required": True,
        "approved": False,
        "pages": {"start_physical_page": 1, "end_physical_page": 1},
        "reason": "No all-valid partition exists without this final semantic tail.",
        "revised_plan_length": 1,
        "estimated_incremental_cost_usd": 0.0,
        "cost_basis": "No paid provider route is selected in Ticket 02.",
    }
    assert approved.status_code == repeated.status_code == 201
    assert approved.json()["plan"]["status"] == "confirmed"
    assert approved.json()["plan"]["plan_id"] == repeated.json()["plan"]["plan_id"]
    assert len(retained.json()["state"]["plan_ids"]) == 2


@pytest.mark.asyncio
async def test_overlong_atomic_unit_remains_blocked_even_when_approval_is_requested(
    tmp_path: Path,
) -> None:
    """Verify approval cannot bypass the hard thirty-minute atomic-unit ceiling.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Imports a deliberately pathological one-line source block and requests approval for
        any short-tail exception to ensure the unrelated flag cannot unlock unsafe packing.
    Outputs:
        None; passes when the plan remains visibly blocked with exact page/unit evidence.
    Failures:
        Fails when an overlong atomic unit is split, approved, or published as confirmed.
    """
    app = create_app(tmp_path)
    pdf = make_planning_pdf(
        page_count=1,
        words_per_page=0,
        chapter_starts={0: "1. Pathological Unit"},
        giant_atomic_words=5000,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, pdf)
        response = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json=valid_plan_request(end_physical_page=1, approve_short_tail=True),
        )

    assert response.status_code == 409
    plan = response.json()["plan"]
    assert plan["status"] == "blocked_source_structure"
    assert plan["listening_sessions"] == []
    assert plan["blocked_atomic_units"]
    assert plan["blocked_atomic_units"][0]["hard_ceiling_exceeded"] is True
    assert plan["blocked_atomic_units"][0]["estimated_minutes"] > 30


@pytest.mark.asyncio
async def test_cross_chapter_and_malformed_requests_fail_without_extraction(
    tmp_path: Path,
) -> None:
    """Probe path traversal, strict JSON typing, cross-chapter, and span-order boundaries.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Sends unusual but plausible hostile or mistaken interactions through the public API.
    Outputs:
        None; passes when each request fails safely and planning storage remains absent.
    Failures:
        Fails when path traversal reaches data, types are coerced, or invalid spans extract.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, make_planning_pdf())
        traversal = await client.get("/api/book-workspaces/..%2F..%2Fruns/chapters")
        strict_type = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json=valid_plan_request(heading_index=True),
        )
        crossing = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json=valid_plan_request(end_physical_page=4),
        )
        reversed_span = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json=valid_plan_request(start_physical_page=3, end_physical_page=1),
        )
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/planning")

    assert traversal.status_code in {404, 422}
    assert strict_type.status_code == 422
    assert crossing.status_code == 422
    assert crossing.json()["error"]["code"] == "cross_chapter_not_allowed"
    assert reversed_span.status_code == 422
    assert reversed_span.json()["error"]["code"] == "invalid_span"
    assert retained.status_code == 404


@pytest.mark.asyncio
async def test_planning_run_traces_scoped_inputs_outputs_and_artifacts(tmp_path: Path) -> None:
    """Verify Ticket 02 function, validation, and artifact events remain reconstructable.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Confirms a plan and reads its durable trace through the public run endpoint.
    Outputs:
        None; passes when causal function spans and bounded source representations are present.
    Failures:
        Fails when tracing omits planning stages, artifacts, correlation, or secret redaction.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id = await import_planning_workspace(client, make_planning_pdf())
        planned = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json=valid_plan_request(),
            headers={"authorization": "Bearer do-not-retain"},
        )
        traced = await client.get(f"/api/runs/{planned.json()['run_id']}")

    assert planned.status_code == 201
    trace = traced.json()
    functions = {event.get("function") for event in trace["events"]}
    assert functions >= {
        "confirm_source_chapter",
        "confirm_chapter_plan",
        "extract_source_index",
        "pack_source_nodes",
        "persist_planning_outcome",
        "normalize_source_text",
    }
    assert len(trace["manifest"]["artifacts"]) == 3
    assert trace["manifest"]["request"] == {
        "method": "POST",
        "path": f"/api/book-workspaces/{workspace_id}/plans",
    }
    serialized = json.dumps(trace)
    assert "do-not-retain" not in serialized
    extraction = next(
        event
        for event in trace["events"]
        if event["event_type"] == "function_completed"
        and event.get("function") == "extract_source_index"
    )
    assert extraction["output"]["span"] == {
        "start_physical_page": 1,
        "end_physical_page": 3,
    }
    traced_nodes = extraction["output"]["nodes"]
    assert isinstance(traced_nodes, list)
    assert any(
        isinstance(node["raw_text"], dict) and node["raw_text"]["type"] == "str"
        for node in traced_nodes
    )


@pytest.mark.asyncio
async def test_browser_surface_exposes_chapter_evidence_and_planning_controls(
    tmp_path: Path,
) -> None:
    """Verify the browser can inspect, adjust, confirm, and approve Ticket 02 plans.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Loads the self-contained browser surface and checks its public control wiring.
    Outputs:
        None; passes when all learner interactions call the Local Orchestrator boundary.
    Failures:
        Fails when chapter evidence, duration, crossing, approval, or fetch wiring is absent.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    for control_id in (
        "planning",
        "active-workspace",
        "inspect-workspace",
        "chapter-heading",
        "chapter-evidence",
        "start-page",
        "end-page",
        "minimum-minutes",
        "maximum-minutes",
        "allow-cross-chapter",
        "approve-short-tail",
        "confirm-chapter",
        "planning-result",
    ):
        assert f'id="{control_id}"' in response.text
    assert "/chapters`" in response.text
    assert "/plans`" in response.text
    assert "inspectRetainedWorkspace" in response.text
    assert "summarizePlanPayload" in response.text
    assert "node_count: nodes.length" in response.text
    assert (
        "planningResult.textContent = JSON.stringify(summarizePlanPayload(payload)" in response.text
    )
