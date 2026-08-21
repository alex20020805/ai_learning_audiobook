import json
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from test_episode_generation import create_confirmed_generation_plan

from ai_learning_audiobook.app import create_app


def inject_source_warning(
    data_root: Path,
    workspace_id: str,
    source_index: dict[str, Any],
    *,
    severity: str,
    code: str,
    message: str = "Synthetic extraction warning for public-boundary review.",
    corrupt_node_text: str | None = None,
) -> tuple[str, Path, str]:
    """Inject deterministic warning evidence into an isolated retained Source Index fixture.

    Inputs:
        data_root: Pytest-owned isolated application root.
        workspace_id: Imported synthetic Book Workspace identity.
        source_index: Public planning response locating the retained index artifact.
        severity: Warning severity under test.
        code: Stable warning code under test.
        message: Learner-visible warning description.
        corrupt_node_text: Optional candidate normalized/raw text requiring correction.
    Functionality:
        Adds one warning to the first planned node and optionally changes its retained test text;
        this simulates deterministic extractor output without exposing a test-only HTTP control.
    Outputs:
        Tuple of affected node identity, artifact path, and original normalized node text.
    Failures:
        Propagates missing fixture, JSON, and filesystem failures.
    """
    source_index_path = (
        data_root
        / "book-workspaces"
        / workspace_id
        / "source-indexes"
        / f"{source_index['source_index_id']}.json"
    )
    retained = json.loads(source_index_path.read_text(encoding="utf-8"))
    node = retained["nodes"][0]
    original_text = str(node["normalized_text"])
    if corrupt_node_text is not None:
        node["raw_text"] = corrupt_node_text
        node["normalized_text"] = corrupt_node_text
    warning = {
        "code": code,
        "severity": severity,
        "message": message,
        "node_id": node["node_id"],
        "physical_page_number": node["page_references"][0]["physical_page_number"],
        "printed_page_label": node["page_references"][0]["printed_page_label"],
    }
    node["warnings"] = [warning]
    retained["warnings"] = [warning]
    source_index_path.write_text(json.dumps(retained, indent=2), encoding="utf-8")
    return str(node["node_id"]), source_index_path, original_text


@pytest.mark.asyncio
async def test_safe_review_approval_is_version_pinned_and_resumes_linked_job(
    tmp_path: Path,
) -> None:
    """Verify safe approval pauses before scripting then produces a linked ready job.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Seeds an approvable review warning, starts generation, inspects complete evidence,
        approves the exact warning, and reads the linked ready Episode and decision trace.
    Outputs:
        None; passes when review is complete, version-pinned, causal, and fidelity-preserving.
    Failures:
        Fails if scripting occurs before approval, decisions float across versions, or source
        coverage changes after approval.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, source_index, plan = await create_confirmed_generation_plan(client)
        node_id, _, _ = inject_source_warning(
            tmp_path,
            workspace_id,
            source_index,
            severity="review_required",
            code="unverified_non_prose_spoken_handling",
        )
        started = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 1},
        )
        assert started.status_code == 409, started.text
        paused = started.json()
        job_id = paused["job"]["job_id"]
        warning = paused["review"]["warnings"][0]
        inspected = await client.get(f"/api/generation-jobs/{job_id}")
        approved = await client.post(
            f"/api/generation-jobs/{job_id}/warnings/{warning['warning_id']}/decisions",
            json={"action": "approve", "correction_text": ""},
        )
        trace = await client.get(f"/api/runs/{approved.json()['run_id']}")
        episode_id = approved.json()["episode"]["episode_id"]
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/episodes/{episode_id}")

    assert paused["job"]["status"] == "awaiting_extraction_review"
    assert paused["job"]["version"] == 1
    assert list(paused["job"]["artifacts"]) == ["extraction_review"]
    assert paused["review"]["warning_count"] == 1
    assert warning["severity"] == "review_required"
    assert warning["approval_allowed"] is True
    assert warning["permitted_actions"] == ["approve", "correct", "rerun", "cancel"]
    assert warning["affected_pages"][0]["physical_page_number"] == 1
    assert warning["node_id"] == node_id
    assert warning["extracted_source"]["sha256"]
    assert warning["evidence"]["geometry"]
    assert warning["proposed_handling"]
    assert warning["expected_impact"]
    assert warning["input_versions"]["source_index_sha256"] == source_index["sha256"]
    assert inspected.json()["review"] == paused["review"]

    assert approved.status_code == 201, approved.text
    outcome = approved.json()
    assert outcome["decision"]["action"] == "approve"
    assert outcome["decision"]["input_versions"] == warning["input_versions"]
    assert outcome["review_parent_job"]["status"] == "review_resolved"
    assert outcome["job"]["review_parent_job_id"] == job_id
    assert outcome["job"]["version"] == 2
    assert outcome["episode"]["status"] == "ready"
    assert outcome["episode"]["extraction_warnings"][0]["warning_id"] == warning["warning_id"]
    assert (
        outcome["episode"]["warning_decisions"][0]["decision_id"]
        == (outcome["decision"]["decision_id"])
    )
    detail = retained.json()
    assert detail["coverage_manifest"]["complete"] is True
    assert detail["script"]["segments"][0]["node_id"] == node_id
    assert detail["extraction_review"]["status"] == "resolved"
    events = trace.json()["events"]
    assert any(event["event_type"] == "warning_decision_recorded" for event in events)
    assert any(
        event["event_type"] == "function_started" and event["function"] == "synthesize_fake_speech"
        for event in events
    )


@pytest.mark.asyncio
async def test_blocking_warning_cannot_be_approved_but_exact_correction_can_continue(
    tmp_path: Path,
) -> None:
    """Verify zero-tolerance blocking evidence never reaches speech without correction.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Seeds an unreadable source marker, attempts forbidden approval, submits an exact source
        correction, and compares the derived script with the unchanged original artifact.
    Outputs:
        None; passes when approval is rejected and correction alone unlocks a ready Episode.
    Failures:
        Fails if blocking work scripts early, mutates extraction, or accepts empty/unsafe action.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, source_index, plan = await create_confirmed_generation_plan(client)
        node_id, source_index_path, _ = inject_source_warning(
            tmp_path,
            workspace_id,
            source_index,
            severity="blocking",
            code="unreadable_replacement_character",
            corrupt_node_text="Unreadable � retained source evidence.",
        )
        started = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 1},
        )
        paused = started.json()
        warning = paused["review"]["warnings"][0]
        forbidden = await client.post(
            f"/api/generation-jobs/{paused['job']['job_id']}/warnings/"
            f"{warning['warning_id']}/decisions",
            json={"action": "approve", "correction_text": ""},
        )
        empty = await client.post(
            f"/api/generation-jobs/{paused['job']['job_id']}/warnings/"
            f"{warning['warning_id']}/decisions",
            json={"action": "correct", "correction_text": "   "},
        )
        corrected_text = "Readable learner-verified source evidence."
        corrected = await client.post(
            f"/api/generation-jobs/{paused['job']['job_id']}/warnings/"
            f"{warning['warning_id']}/decisions",
            json={"action": "correct", "correction_text": corrected_text},
        )
        original_trace = await client.get(f"/api/runs/{started.json()['run_id']}")
        episode_id = corrected.json()["episode"]["episode_id"]
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/episodes/{episode_id}")

    assert started.status_code == 409
    assert paused["job"]["status"] == "blocked_extraction"
    assert warning["approval_allowed"] is False
    assert "approve" not in warning["permitted_actions"]
    assert forbidden.status_code == 409
    assert forbidden.json()["error"]["code"] == "warning_not_approvable"
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "invalid_warning_correction"
    assert corrected.status_code == 201, corrected.text
    detail = retained.json()
    corrected_segment = next(
        segment for segment in detail["script"]["segments"] if segment["node_id"] == node_id
    )
    assert corrected_segment["spoken_text"] == corrected_text
    assert any(
        entry["operation"]["operation"] == "learner_evidence_correction"
        for entry in detail["transformation_report"]["entries"]
        if entry["node_id"] == node_id and entry["kind"] == "normalization"
    )
    immutable_original = json.loads(source_index_path.read_text(encoding="utf-8"))
    original_node = next(node for node in immutable_original["nodes"] if node["node_id"] == node_id)
    assert original_node["normalized_text"] == "Unreadable � retained source evidence."
    original_events = original_trace.json()["events"]
    assert not any(
        event.get("function") == "build_verbatim_script"
        for event in original_events
        if event["event_type"] == "function_started"
    )
    assert not any(
        event.get("function") == "synthesize_fake_speech"
        for event in original_events
        if event["event_type"] == "function_started"
    )


@pytest.mark.asyncio
async def test_review_rerun_can_pause_again_and_then_cancel_without_publication(
    tmp_path: Path,
) -> None:
    """Verify compatible rerun remains honest when evidence is unchanged and can be cancelled.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Requests a deterministic rerun for unresolved review evidence, observes a linked second
        paused job, cancels it, and inspects queue and Episode collections.
    Outputs:
        None; passes when unchanged evidence pauses again and cancellation publishes nothing.
    Failures:
        Fails if rerun silently approves, overwrites a job, or leaves active/ready work.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, source_index, plan = await create_confirmed_generation_plan(client)
        inject_source_warning(
            tmp_path,
            workspace_id,
            source_index,
            severity="review_required",
            code="suspected_text_corruption",
        )
        first = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 1},
        )
        first_payload = first.json()
        first_warning_id = first_payload["review"]["warnings"][0]["warning_id"]
        rerun = await client.post(
            f"/api/generation-jobs/{first_payload['job']['job_id']}/warnings/"
            f"{first_warning_id}/decisions",
            json={"action": "rerun", "correction_text": ""},
        )
        second_payload = rerun.json()
        second_warning_id = second_payload["review"]["warnings"][0]["warning_id"]
        cancelled = await client.post(
            f"/api/generation-jobs/{second_payload['job']['job_id']}/warnings/"
            f"{second_warning_id}/decisions",
            json={"action": "cancel", "correction_text": ""},
        )
        queue = await client.get("/api/generation-queue")
        episodes = await client.get(f"/api/book-workspaces/{workspace_id}/episodes")

    assert rerun.status_code == 409
    assert first_payload["job"]["job_id"] != second_payload["job"]["job_id"]
    assert second_payload["job"]["version"] == 2
    assert second_payload["job"]["review_parent_job_id"] == first_payload["job"]["job_id"]
    assert second_payload["job"]["status"] == "awaiting_extraction_review"
    assert second_warning_id == first_warning_id
    assert cancelled.status_code == 200
    assert cancelled.json()["job"]["status"] == "cancelled"
    assert [entry["status"] for entry in queue.json()["queue"]["entries"]] == [
        "rerun_requested",
        "cancelled",
    ]
    assert queue.json()["queue"]["active_job_count"] == 0
    assert episodes.json()["episodes"] == []


@pytest.mark.asyncio
async def test_informational_warning_continues_and_remains_in_final_evidence(
    tmp_path: Path,
) -> None:
    """Verify informational extraction evidence never creates unnecessary intervention.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Seeds an informational warning, generates normally, and inspects final Episode evidence.
    Outputs:
        None; passes when generation is ready without a decision and retains the warning.
    Failures:
        Fails if informational evidence pauses, disappears, or receives a fabricated decision.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        workspace_id, source_index, plan = await create_confirmed_generation_plan(client)
        inject_source_warning(
            tmp_path,
            workspace_id,
            source_index,
            severity="informational",
            code="blank_page",
        )
        generated = await client.post(
            f"/api/book-workspaces/{workspace_id}/episodes",
            json={"plan_id": plan["plan_id"], "session_number": 1},
        )
        episode_id = generated.json()["episode"]["episode_id"]
        retained = await client.get(f"/api/book-workspaces/{workspace_id}/episodes/{episode_id}")

    assert generated.status_code == 201, generated.text
    assert generated.json()["episode"]["status"] == "ready"
    assert generated.json()["episode"]["extraction_warnings"][0]["severity"] == "informational"
    assert generated.json()["episode"]["warning_decisions"] == []
    assert retained.json()["extraction_review"]["status"] == "clean"
    assert retained.json()["extraction_review"]["warnings"][0]["code"] == "blank_page"


@pytest.mark.asyncio
async def test_browser_surface_exposes_evidence_backed_warning_decisions(tmp_path: Path) -> None:
    """Verify the private browser can inspect and act on exact extraction warnings.

    Inputs:
        tmp_path: Pytest-owned isolated application data root.
    Functionality:
        Loads the browser HTML and checks review evidence, correction, action, and decision wiring.
    Outputs:
        None; passes when all Ticket 04 controls use public job/warning endpoints.
    Failures:
        Fails when review cannot be restored, corrected, rerun, approved safely, or cancelled.
    """
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    for control_id in (
        "extraction-review",
        "review-warning",
        "review-result",
        "review-action",
        "correction-text",
        "apply-review-decision",
        "review-status",
    ):
        assert f'id="{control_id}"' in response.text
    assert "/api/generation-jobs/${paused.job_id}" in response.text
    assert "submitReviewDecision" in response.text
    assert "restorePendingReview" in response.text
    assert "extraction_warning_count" in response.text
    assert "warning_decision_count" in response.text
