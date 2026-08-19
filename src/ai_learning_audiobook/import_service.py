"""Native Source Document import behavior behind the HTTP boundary."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any, TypedDict

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pypdf.generic import Destination

from ai_learning_audiobook.tracing import record_artifact, traced


class SourceRejected(Exception):
    """Carries a stable, actionable Source Document rejection reason."""

    def __init__(self, code: str, message: str) -> None:
        """Create a Source Document rejection.

        Inputs:
            code: Stable machine-readable public error code.
            message: Human-readable learner guidance.
        Functionality:
            Stores the rejection contract while preserving normal exception behavior.
        Outputs:
            None; initializes this exception.
        Failures:
            Does not raise for valid strings.
        """
        super().__init__(message)
        self.code = code
        self.message = message


class SourceInspection(TypedDict):
    """Validated fast structural evidence for a native-text Source Document."""

    page_count: int
    page_texts: list[str]
    document_title: str
    headings: list[dict[str, Any]]


class ImportOutcome(TypedDict):
    """Public import behavior returned to the HTTP adapter."""

    reopened: bool
    workspace: dict[str, Any]


@traced
def detect_top_level_headings(reader: PdfReader, first_page_text: str) -> list[dict[str, Any]]:
    """Detect provisional top-level structure using the strongest available evidence.

    Inputs:
        reader: Successfully opened PDF reader with page and outline access.
        first_page_text: Native text extracted from the first physical page.
    Functionality:
        Prefers top-level PDF destinations and their resolved pages, then falls back to the
        first visible non-empty line when the document supplies no outline.
    Outputs:
        Ordered heading mappings with title, physical page number, and evidence source.
    Failures:
        Ignores individually unresolvable outline destinations and otherwise returns fallback
        evidence; propagates unexpected reader failures.
    """
    headings: list[dict[str, Any]] = []
    for outline_item in reader.outline:
        if not isinstance(outline_item, Destination):
            continue
        page_index = reader.get_destination_page_number(outline_item)
        if page_index is None or page_index < 0:
            continue
        headings.append(
            {
                "title": outline_item.title,
                "physical_page_number": page_index + 1,
                "evidence": "pdf_outline",
            }
        )
    if headings:
        return headings

    return [
        {
            "title": line.strip(),
            "physical_page_number": 1,
            "evidence": "visible_text",
        }
        for line in first_page_text.splitlines()
        if line.strip()
    ][:1]


@traced
def inspect_source_document(source_bytes: bytes) -> SourceInspection:
    """Validate and fast-scan one native-text Source Document.

    Inputs:
        source_bytes: Complete immutable PDF bytes supplied by the learner.
    Functionality:
        Parses pages, rejects encrypted/corrupt/scan-heavy inputs, extracts provisional
        text, and detects the first visible heading for the import result.
    Outputs:
        SourceInspection containing page count, page text, title, and heading evidence.
    Failures:
        Raises SourceRejected with a stable code when the source is unsuitable.
    """
    try:
        reader = PdfReader(BytesIO(source_bytes))
        if reader.is_encrypted:
            raise SourceRejected("password_blocked", "The Source Document requires a password.")
        page_texts = [(page.extract_text() or "") for page in reader.pages]
    except SourceRejected:
        raise
    except (PdfReadError, OSError, ValueError) as error:
        raise SourceRejected(
            "corrupt_pdf", "The Source Document could not be parsed as a PDF."
        ) from error

    if (
        not page_texts
        or sum(len(text.strip()) < 20 for text in page_texts) / len(page_texts) > 0.10
    ):
        raise SourceRejected(
            "scan_heavy", "The Source Document does not contain enough native text."
        )

    first_page_text = page_texts[0]
    headings = detect_top_level_headings(reader, first_page_text)
    document_title = str(reader.metadata.title or "") if reader.metadata else ""
    return {
        "page_count": len(page_texts),
        "page_texts": page_texts,
        "document_title": document_title,
        "headings": headings,
    }


@traced
def publish_book_workspace(
    *,
    data_root: Path,
    source_bytes: bytes,
    filename: str,
    source_hash: str,
    inspection: SourceInspection,
) -> dict[str, Any]:
    """Atomically publish a validated Source Document and Book Workspace record.

    Inputs:
        data_root: Writable root dedicated to application data.
        source_bytes: Validated immutable PDF bytes.
        filename: Original learner-facing filename.
        source_hash: SHA-256 identity of the source bytes.
        inspection: Successful fast structural inspection.
    Functionality:
        Links changed content with a shared PDF title to its prior edition, atomically
        writes source and metadata, and records both artifacts in the active run.
    Outputs:
        The public Book Workspace representation.
    Failures:
        Propagates filesystem and JSON errors; temporary files never appear as workspaces.
    """
    workspaces_root = data_root / "book-workspaces"
    workspace_root = workspaces_root / source_hash
    workspace_root.mkdir(parents=True, exist_ok=False)

    edition_of: str | None = None
    for candidate_path in workspaces_root.glob("*/workspace.json"):
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        if candidate["source_document"].get("document_title") == inspection["document_title"]:
            edition_of = str(candidate["workspace_id"])
            break

    workspace: dict[str, Any] = {
        "workspace_id": source_hash,
        "source_document": {
            "filename": filename,
            "sha256": source_hash,
            "page_count": inspection["page_count"],
            "document_title": inspection["document_title"],
            "edition_of": edition_of,
        },
        "structural_scan": {"status": "complete", "headings": inspection["headings"]},
        "validation": {"outcome": "accepted", "warnings": []},
    }

    source_path = workspace_root / "source.pdf"
    source_temporary = source_path.with_suffix(".pdf.tmp")
    source_temporary.write_bytes(source_bytes)
    source_temporary.replace(source_path)
    record_artifact(source_path, media_type="application/pdf", sha256=source_hash)

    workspace_path = workspace_root / "workspace.json"
    workspace_bytes = json.dumps(workspace, indent=2, sort_keys=True).encode("utf-8")
    workspace_temporary = workspace_path.with_suffix(".json.tmp")
    workspace_temporary.write_bytes(workspace_bytes)
    workspace_temporary.replace(workspace_path)
    record_artifact(
        workspace_path,
        media_type="application/vnd.ai-learning.book-workspace+json",
        sha256=hashlib.sha256(workspace_bytes).hexdigest(),
    )
    return workspace


@traced
def import_source_document_content(
    *, data_root: Path, source_bytes: bytes, filename: str
) -> ImportOutcome:
    """Create or reopen a content-addressed Book Workspace.

    Inputs:
        data_root: Writable root dedicated to application data.
        source_bytes: Complete PDF request body.
        filename: Original learner-facing filename.
    Functionality:
        Reopens identical immutable content or validates and publishes a new edition.
    Outputs:
        ImportOutcome containing reopening state and public workspace representation.
    Failures:
        Raises SourceRejected for unsuitable PDFs and propagates durable storage errors.
    """
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    workspace_path = data_root / "book-workspaces" / source_hash / "workspace.json"
    if workspace_path.exists():
        return {
            "reopened": True,
            "workspace": json.loads(workspace_path.read_text(encoding="utf-8")),
        }

    inspection = inspect_source_document(source_bytes)
    workspace = publish_book_workspace(
        data_root=data_root,
        source_bytes=source_bytes,
        filename=filename,
        source_hash=source_hash,
        inspection=inspection,
    )
    return {"reopened": False, "workspace": workspace}


@traced
def list_published_book_workspaces(data_root: Path) -> list[dict[str, Any]]:
    """List successfully published Book Workspaces.

    Inputs:
        data_root: Application data root containing Book Workspace directories.
    Functionality:
        Reads only final workspace records and ignores temporary or rejected artifacts.
    Outputs:
        Ordered public Book Workspace representations.
    Failures:
        Propagates filesystem and JSON errors from corrupt retained application data.
    """
    workspace_paths = sorted((data_root / "book-workspaces").glob("*/workspace.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in workspace_paths]
