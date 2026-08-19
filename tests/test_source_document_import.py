from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas

from ai_learning_audiobook.app import create_app


def make_native_text_pdf(title: str, body: str) -> bytes:
    """Create a small native-text PDF fixture.

    Inputs:
        title: Visible heading text required to be non-empty.
        body: Visible prose text required to be non-empty.
    Functionality:
        Renders a single-page PDF with a heading and prose for HTTP import tests.
    Outputs:
        PDF bytes suitable for submission as an application/pdf request body.
    Failures:
        Propagates ReportLab errors when the fixture cannot be rendered.
    """
    output = BytesIO()
    canvas = Canvas(output)
    canvas.setTitle(title)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(72, 740, title)
    canvas.setFont("Helvetica", 12)
    canvas.drawString(72, 710, body)
    canvas.save()
    return output.getvalue()


def make_rejected_pdf(kind: str) -> bytes:
    """Create a corrupt, password-blocked, or scan-heavy PDF fixture.

    Inputs:
        kind: One of `corrupt`, `password_blocked`, or `scan_heavy`.
    Functionality:
        Builds the requested rejection case without relying on external files.
    Outputs:
        Bytes that exercise one documented Source Document rejection path.
    Failures:
        Raises ValueError when `kind` does not name a supported fixture.
    """
    if kind == "corrupt":
        return b"not a pdf"
    if kind == "scan_heavy":
        output = BytesIO()
        canvas = Canvas(output)
        image = Image.new("RGB", (500, 700), color="white")
        canvas.drawInlineImage(image, 48, 70, width=500, height=700)
        canvas.showPage()
        canvas.save()
        return output.getvalue()
    if kind == "password_blocked":
        reader = PdfReader(BytesIO(make_native_text_pdf("Locked", "Private text.")))
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.encrypt("secret")
        output = BytesIO()
        writer.write(output)
        return output.getvalue()
    raise ValueError(f"Unsupported rejected PDF kind: {kind}")


def make_outlined_pdf(outline_title: str) -> bytes:
    """Create a native-text PDF whose structural heading comes from its outline.

    Inputs:
        outline_title: Top-level bookmark title required to be non-empty.
    Functionality:
        Renders cover-like prose and attaches a top-level destination with a distinct title.
    Outputs:
        PDF bytes carrying both native text and outline structure.
    Failures:
        Propagates ReportLab errors when the fixture cannot be rendered.
    """
    output = BytesIO()
    canvas = Canvas(output)
    canvas.bookmarkPage("chapter-one")
    canvas.addOutlineEntry(outline_title, "chapter-one", level=0)
    canvas.drawString(72, 740, "Cover material with enough native text for validation.")
    canvas.save()
    return output.getvalue()


@pytest.mark.asyncio
async def test_learner_can_import_a_native_text_source_document(tmp_path: Path) -> None:
    """Verify that an acceptable PDF creates a visible Book Workspace.

    Inputs:
        tmp_path: Pytest-owned isolated storage directory.
    Functionality:
        Imports a native-text PDF through the public HTTP boundary and observes
        the resulting Book Workspace representation.
    Outputs:
        None; the test passes when the response matches the public contract.
    Failures:
        Fails when import is rejected or required workspace evidence is absent.
    """
    app = create_app(data_root=tmp_path)
    pdf = make_native_text_pdf("Chapter One", "Trustworthy systems preserve evidence.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/book-workspaces/import",
            content=pdf,
            headers={
                "content-type": "application/pdf",
                "x-source-filename": "example.pdf",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["reopened"] is False
    assert payload["workspace"]["source_document"]["filename"] == "example.pdf"
    assert payload["workspace"]["source_document"]["page_count"] == 1
    assert payload["workspace"]["structural_scan"]["status"] == "complete"
    assert payload["workspace"]["structural_scan"]["headings"][0]["title"] == "Chapter One"
    assert payload["workspace"]["validation"]["outcome"] == "accepted"
    assert payload["run_id"]


@pytest.mark.asyncio
async def test_identical_content_reopens_and_changed_content_creates_an_edition(
    tmp_path: Path,
) -> None:
    """Verify immutable content identity across repeated imports.

    Inputs:
        tmp_path: Pytest-owned isolated storage directory.
    Functionality:
        Imports identical bytes twice and different bytes once through the public API.
    Outputs:
        None; the test passes when identity and reopening are externally correct.
    Failures:
        Fails when filename changes duplicate content or changed bytes reuse an identity.
    """
    app = create_app(data_root=tmp_path)
    original = make_native_text_pdf("Chapter One", "The original edition.")
    changed = make_native_text_pdf("Chapter One", "A corrected second edition.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/api/book-workspaces/import",
            content=original,
            headers={"content-type": "application/pdf", "x-source-filename": "first.pdf"},
        )
        reopened = await client.post(
            "/api/book-workspaces/import",
            content=original,
            headers={"content-type": "application/pdf", "x-source-filename": "renamed.pdf"},
        )
        edition = await client.post(
            "/api/book-workspaces/import",
            content=changed,
            headers={"content-type": "application/pdf", "x-source-filename": "second.pdf"},
        )

    assert first.status_code == 201
    assert reopened.status_code == 200
    assert reopened.json()["reopened"] is True
    assert reopened.json()["workspace"]["workspace_id"] == first.json()["workspace"]["workspace_id"]
    assert reopened.json()["workspace"]["source_document"]["filename"] == "first.pdf"
    assert edition.status_code == 201
    assert edition.json()["reopened"] is False
    assert edition.json()["workspace"]["workspace_id"] != first.json()["workspace"]["workspace_id"]
    assert (
        edition.json()["workspace"]["source_document"]["edition_of"]
        == first.json()["workspace"]["workspace_id"]
    )


@pytest.mark.parametrize(
    ("kind", "error_code"),
    [
        ("corrupt", "corrupt_pdf"),
        ("password_blocked", "password_blocked"),
        ("scan_heavy", "scan_heavy"),
    ],
)
@pytest.mark.asyncio
async def test_unacceptable_source_document_is_rejected_without_a_partial_workspace(
    tmp_path: Path, kind: str, error_code: str
) -> None:
    """Verify that unsafe PDF inputs fail cleanly at the HTTP boundary.

    Inputs:
        tmp_path: Pytest-owned isolated storage directory.
        kind: Rejection fixture selected by the parameter table.
        error_code: Stable public reason expected for that fixture.
    Functionality:
        Attempts import, then lists workspaces to detect accidental publication.
    Outputs:
        None; the test passes when rejection is actionable and storage remains empty.
    Failures:
        Fails when an unsafe input is accepted, crashes, or leaves a visible workspace.
    """
    app = create_app(data_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/book-workspaces/import",
            content=make_rejected_pdf(kind),
            headers={"content-type": "application/pdf", "x-source-filename": "unsafe.pdf"},
        )
        workspaces = await client.get("/api/book-workspaces")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == error_code
    assert workspaces.status_code == 200
    assert workspaces.json() == {"workspaces": []}


@pytest.mark.asyncio
async def test_import_run_exposes_correlated_function_and_artifact_traces(
    tmp_path: Path,
) -> None:
    """Verify durable, bounded input/output tracing through the public API.

    Inputs:
        tmp_path: Pytest-owned isolated storage directory.
    Functionality:
        Imports a PDF and retrieves the resulting run manifest through HTTP.
    Outputs:
        None; the test passes when causal events and bounded binary metadata are visible.
    Failures:
        Fails when events are missing, uncorrelated, or contain the full PDF payload.
    """
    app = create_app(data_root=tmp_path)
    pdf = make_native_text_pdf("Traceable Chapter", "Evidence connects every stage.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        imported = await client.post(
            "/api/book-workspaces/import",
            content=pdf,
            headers={
                "content-type": "application/pdf",
                "x-source-filename": "traceable.pdf",
                "authorization": "Bearer must-not-be-logged",
            },
        )
        run_id = imported.json()["run_id"]
        traced = await client.get(f"/api/runs/{run_id}")

    assert traced.status_code == 200
    trace = traced.json()
    assert trace["manifest"]["run_id"] == run_id
    assert trace["manifest"]["outcome"] == "completed"
    assert {event["event_type"] for event in trace["events"]} >= {
        "request_received",
        "function_started",
        "function_completed",
        "artifact_written",
        "request_completed",
    }
    assert {event.get("function") for event in trace["events"]} >= {
        "import_source_document",
        "inspect_source_document",
        "publish_book_workspace",
    }
    received = next(event for event in trace["events"] if event["event_type"] == "request_received")
    assert received["body"] == {
        "type": "bytes",
        "size": len(pdf),
        "sha256": imported.json()["workspace"]["source_document"]["sha256"],
    }
    serialized = str(trace)
    assert "must-not-be-logged" not in serialized
    assert pdf.hex() not in serialized


@pytest.mark.asyncio
async def test_private_browser_surface_exposes_import_and_workspace_results(tmp_path: Path) -> None:
    """Verify that the loopback application provides the Ticket 01 browser surface.

    Inputs:
        tmp_path: Pytest-owned isolated storage directory.
    Functionality:
        Loads the private application root through the public HTTP boundary.
    Outputs:
        None; the test passes when import controls and result regions are present.
    Failures:
        Fails when the browser surface cannot initiate import or render workspace evidence.
    """
    app = create_app(data_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="source-document"' in response.text
    assert 'id="import-source-document"' in response.text
    assert 'id="workspace-result"' in response.text
    assert 'fetch("/api/book-workspaces/import"' in response.text


@pytest.mark.asyncio
async def test_structural_scan_prefers_top_level_pdf_outline_evidence(tmp_path: Path) -> None:
    """Verify outline-first chapter detection through the public import API.

    Inputs:
        tmp_path: Pytest-owned isolated storage directory.
    Functionality:
        Imports a native PDF whose visible cover text differs from its structural bookmark.
    Outputs:
        None; the test passes when the outline title and destination page are exposed.
    Failures:
        Fails when structural scan mistakes cover prose for the chapter hierarchy.
    """
    app = create_app(data_root=tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/book-workspaces/import",
            content=make_outlined_pdf("Chapter One: Foundations"),
            headers={"content-type": "application/pdf", "x-source-filename": "outlined.pdf"},
        )

    assert response.status_code == 201
    assert response.json()["workspace"]["structural_scan"]["headings"] == [
        {
            "title": "Chapter One: Foundations",
            "physical_page_number": 1,
            "evidence": "pdf_outline",
        }
    ]
