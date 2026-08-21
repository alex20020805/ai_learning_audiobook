"""Run a retained HTTP-boundary chapter-planning smoke test for a private PDF."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any, cast

from httpx import ASGITransport, AsyncClient

from ai_learning_audiobook.app import create_app


def choose_heading(chapters: list[dict[str, Any]], start_page: int) -> int:
    """Choose the closest detected heading at or before a requested start page.

    Inputs:
        chapters: Ordered chapter catalog returned by the public HTTP API.
        start_page: One-based physical page where the requested selection begins.
    Functionality:
        Selects the last heading whose suggested start does not follow the requested page.
    Outputs:
        Zero-based heading index suitable for a planning request.
    Failures:
        Raises ValueError when no detected heading precedes the requested page.
    """
    eligible = [
        chapter
        for chapter in chapters
        if int(cast(dict[str, Any], chapter["suggested_span"])["start_physical_page"]) <= start_page
    ]
    if not eligible:
        raise ValueError("No detected heading begins at or before the requested start page")
    return int(eligible[-1]["heading_index"])


async def smoke_plan(
    source_path: Path,
    data_root: Path,
    *,
    start_page: int,
    end_page: int,
    minimum_minutes: float,
    maximum_minutes: float,
    approve_short_tail: bool,
) -> dict[str, object]:
    """Import and plan one private Source Document span through public HTTP seams.

    Inputs:
        source_path: Learner-authorized native-text PDF path.
        data_root: Persistent ignored directory for workspace artifacts and trace runs.
        start_page: Inclusive one-based physical extraction start.
        end_page: Inclusive one-based physical extraction end.
        minimum_minutes: Requested lower Episode duration bound.
        maximum_minutes: Requested upper Episode duration bound.
        approve_short_tail: Explicit approval for an exact short-tail proposal.
    Functionality:
        Imports or reopens the workspace, inspects chapters, selects relevant heading evidence,
        confirms the requested span, and returns only bounded plan/trace metadata.
    Outputs:
        Summary mapping with status, identities, node types, warnings, and session durations.
    Failures:
        Propagates unreadable-file, HTTP client, and unexpected application failures.
    """
    app = create_app(data_root)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=300
    ) as client:
        imported = await client.post(
            "/api/book-workspaces/import",
            content=source_path.read_bytes(),
            headers={
                "content-type": "application/pdf",
                "x-source-filename": source_path.name,
            },
        )
        imported.raise_for_status()
        workspace_id = str(imported.json()["workspace"]["workspace_id"])
        catalog_response = await client.get(f"/api/book-workspaces/{workspace_id}/chapters")
        catalog_response.raise_for_status()
        chapters = cast(list[dict[str, Any]], catalog_response.json()["chapters"])
        heading_index = choose_heading(chapters, start_page)
        selected = chapters[heading_index]
        suggested_end = int(cast(dict[str, Any], selected["suggested_span"])["end_physical_page"])
        planned = await client.post(
            f"/api/book-workspaces/{workspace_id}/plans",
            json={
                "heading_index": heading_index,
                "start_physical_page": start_page,
                "end_physical_page": end_page,
                "minimum_minutes": minimum_minutes,
                "maximum_minutes": maximum_minutes,
                "allow_cross_chapter": end_page > suggested_end,
                "approve_short_tail": approve_short_tail,
                "boundary_note": "Ticket 02 retained real-document smoke selection.",
            },
        )
    payload = planned.json()
    source_index = cast(dict[str, Any], payload.get("source_index", {}))
    plan = cast(dict[str, Any], payload.get("plan", {}))
    nodes = cast(list[dict[str, Any]], source_index.get("nodes", []))
    sessions = cast(list[dict[str, Any]], plan.get("listening_sessions", []))
    return {
        "status": planned.status_code,
        "run_id": payload.get("run_id"),
        "workspace_id": workspace_id,
        "selected_heading": selected["title"],
        "source_index_sha256": source_index.get("sha256"),
        "node_count": len(nodes),
        "node_types": sorted({str(node["type"]) for node in nodes}),
        "warning_count": len(cast(list[object], source_index.get("warnings", []))),
        "plan_id": plan.get("plan_id"),
        "plan_status": plan.get("status"),
        "session_minutes": [round(float(session["estimated_minutes"]), 2) for session in sessions],
        "error": payload.get("error"),
    }


def main() -> None:
    """Parse retained smoke-plan arguments and print a bounded summary.

    Inputs:
        None; reads command-line arguments.
    Functionality:
        Runs one asynchronous real-document planning smoke test with explicit page/policy input.
    Outputs:
        None; prints one bounded summary mapping to standard output.
    Failures:
        Propagates argument, fixture, HTTP, and planning failures with nonzero process exit.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("data_root", type=Path)
    parser.add_argument("--start-page", type=int, required=True)
    parser.add_argument("--end-page", type=int, required=True)
    parser.add_argument("--minimum-minutes", type=float, default=15.0)
    parser.add_argument("--maximum-minutes", type=float, default=25.0)
    parser.add_argument("--approve-short-tail", action="store_true")
    arguments = parser.parse_args()
    summary = asyncio.run(
        smoke_plan(
            arguments.source,
            arguments.data_root,
            start_page=arguments.start_page,
            end_page=arguments.end_page,
            minimum_minutes=arguments.minimum_minutes,
            maximum_minutes=arguments.maximum_minutes,
            approve_short_tail=arguments.approve_short_tail,
        )
    )
    print(summary)


if __name__ == "__main__":
    main()
