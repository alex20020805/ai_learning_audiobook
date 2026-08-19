"""Run a non-retaining HTTP-boundary smoke import for a private PDF fixture."""

from __future__ import annotations

import argparse
import asyncio
import tempfile
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from ai_learning_audiobook.app import create_app


async def smoke_import(source_path: Path) -> dict[str, object]:
    """Import a private Source Document through the public HTTP seam once.

    Inputs:
        source_path: Readable path to a learner-authorized native-text PDF.
    Functionality:
        Creates isolated temporary application storage, imports the PDF through ASGI, and
        returns a bounded summary without retaining or printing source content.
    Outputs:
        Mapping with HTTP status, run identity, validation, page count, and error details.
    Failures:
        Propagates unreadable-file, HTTP client, and unexpected application failures.
    """
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Path(directory))
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", timeout=180
        ) as client:
            response = await client.post(
                "/api/book-workspaces/import",
                content=source_path.read_bytes(),
                headers={
                    "content-type": "application/pdf",
                    "x-source-filename": source_path.name,
                },
            )
        payload = response.json()
        workspace = payload.get("workspace", {})
        source_document = workspace.get("source_document", {})
        structural_scan = workspace.get("structural_scan", {})
        validation = workspace.get("validation", {})
        return {
            "status": response.status_code,
            "run_id": payload.get("run_id"),
            "page_count": source_document.get("page_count"),
            "validation": validation.get("outcome"),
            "warning_count": len(validation.get("warnings", [])),
            "heading_count": len(structural_scan.get("headings", [])),
            "error": payload.get("error"),
        }


def main() -> None:
    """Run the private-fixture smoke import command.

    Inputs:
        None; parses one PDF path from command-line arguments.
    Functionality:
        Executes the asynchronous smoke import and prints only its bounded summary.
    Outputs:
        None; writes one summary mapping to standard output.
    Failures:
        Propagates argument, fixture, and smoke-import failures with a nonzero process exit.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    arguments = parser.parse_args()
    print(asyncio.run(smoke_import(arguments.source)))


if __name__ == "__main__":
    main()
