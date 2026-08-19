"""Native Source Document import behavior behind the HTTP boundary."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import NotRequired, TypedDict, cast
from uuid import uuid4

import pdfplumber
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
    headings: list[Heading]
    warnings: list[StructureWarning]


class HeadingEvidence(TypedDict):
    """Evidence used to propose one structural heading."""

    outline_title: NotRequired[str]
    visible_heading: str
    sources: list[str]


class Heading(TypedDict):
    """Provisional structural heading with physical and printed-page provenance."""

    title: str
    physical_page_number: int
    printed_page_label: str
    evidence: HeadingEvidence


class StructureWarning(TypedDict):
    """Inspectable disagreement between outline and visible-heading evidence."""

    code: str
    physical_page_number: int
    printed_page_label: str
    outline_title: str
    visible_heading: str


class SourceDocumentRecord(TypedDict):
    """Immutable Source Document identity retained by a Book Workspace."""

    filename: str
    sha256: str
    page_count: int
    document_title: str
    edition_of: str | None
    artifact_ref: str


class StructuralScanRecord(TypedDict):
    """Fast structural scan exposed after successful import."""

    status: str
    headings: list[Heading]


class ValidationRecord(TypedDict):
    """Public Source Document validation outcome and evidence warnings."""

    outcome: str
    warnings: list[StructureWarning]


class BookWorkspace(TypedDict):
    """Public persistent Book Workspace representation for Ticket 01."""

    workspace_id: str
    source_document: SourceDocumentRecord
    structural_scan: StructuralScanRecord
    validation: ValidationRecord


class ImportOutcome(TypedDict):
    """Public import behavior returned to the HTTP adapter."""

    reopened: bool
    workspace: BookWorkspace


@traced
def is_scan_heavy(source_bytes: bytes, page_texts: list[str]) -> bool:
    """Classify raster-dominant low-text pages without penalizing blank dividers.

    Inputs:
        source_bytes: Complete parseable PDF bytes.
        page_texts: Native text extracted for each physical page.
    Functionality:
        Counts nonblank pages and marks a page scan-suspected only when it has fewer than
        twenty printable characters plus a raster image covering over half the page.
    Outputs:
        True when scan-suspected pages exceed ten percent of nonblank pages or no substantive
        native-text page exists; otherwise False.
    Failures:
        Propagates pdfplumber parsing failures for a PDF that passed initial pypdf parsing.
    """
    nonblank_pages = 0
    scan_suspected_pages = 0
    native_text_pages = 0
    with pdfplumber.open(BytesIO(source_bytes)) as document:
        for page_index, page in enumerate(document.pages):
            text = page_texts[page_index].strip()
            images = page.images
            if text or images:
                nonblank_pages += 1
            if len(text) >= 20:
                native_text_pages += 1
            page_area = float(page.width) * float(page.height)
            has_large_raster = any(
                (float(image["x1"]) - float(image["x0"]))
                * (float(image["bottom"]) - float(image["top"]))
                > page_area * 0.5
                for image in images
            )
            if len(text) < 20 and has_large_raster:
                scan_suspected_pages += 1
    if native_text_pages == 0:
        return True
    return nonblank_pages > 0 and scan_suspected_pages / nonblank_pages > 0.10


@traced
def detect_top_level_headings(
    reader: PdfReader, page_texts: list[str]
) -> tuple[list[Heading], list[StructureWarning]]:
    """Detect provisional top-level structure using the strongest available evidence.

    Inputs:
        reader: Successfully opened PDF reader with page and outline access.
        page_texts: Native text extracted from every physical page in document order.
    Functionality:
        Prefers top-level PDF destinations and their resolved pages, then falls back to the
        first visible non-empty line when the document supplies no outline.
    Outputs:
        Ordered heading mappings plus warnings for outline/visible-heading disagreement.
    Failures:
        Ignores individually unresolvable outline destinations and otherwise returns fallback
        evidence; propagates unexpected reader failures.
    """
    headings: list[Heading] = []
    warnings: list[StructureWarning] = []
    page_labels = reader.page_labels
    for outline_item in reader.outline:
        if not isinstance(outline_item, Destination):
            continue
        page_index = reader.get_destination_page_number(outline_item)
        if page_index is None or page_index < 0:
            continue
        visible_heading = next(
            (line.strip() for line in page_texts[page_index].splitlines() if line.strip()),
            "",
        )
        printed_page_label = page_labels[page_index]
        outline_title = str(outline_item.title or "")
        headings.append(
            {
                "title": outline_title,
                "physical_page_number": page_index + 1,
                "printed_page_label": printed_page_label,
                "evidence": {
                    "outline_title": outline_title,
                    "visible_heading": visible_heading,
                    "sources": ["pdf_outline", "visible_heading"],
                },
            }
        )
        if outline_title.casefold().strip() != visible_heading.casefold().strip():
            warnings.append(
                {
                    "code": "outline_visible_heading_mismatch",
                    "physical_page_number": page_index + 1,
                    "printed_page_label": printed_page_label,
                    "outline_title": outline_title,
                    "visible_heading": visible_heading,
                }
            )
    if headings:
        return headings, warnings

    first_page_text = page_texts[0]
    fallback: list[Heading] = []
    fallback_heading = next(
        (line.strip() for line in first_page_text.splitlines() if line.strip()), None
    )
    if fallback_heading is not None:
        fallback.append(
            Heading(
                title=fallback_heading,
                physical_page_number=1,
                printed_page_label=page_labels[0],
                evidence=HeadingEvidence(
                    visible_heading=fallback_heading, sources=["visible_heading"]
                ),
            )
        )
    return fallback, warnings


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

    if not page_texts or is_scan_heavy(source_bytes, page_texts):
        raise SourceRejected(
            "scan_heavy", "The Source Document does not contain enough native text."
        )

    headings, warnings = detect_top_level_headings(reader, page_texts)
    document_title = str(reader.metadata.title or "") if reader.metadata else ""
    return {
        "page_count": len(page_texts),
        "page_texts": page_texts,
        "document_title": document_title,
        "headings": headings,
        "warnings": warnings,
    }


@traced
def publish_book_workspace(
    *,
    data_root: Path,
    source_bytes: bytes,
    filename: str,
    source_hash: str,
    inspection: SourceInspection,
    edition_of: str | None,
) -> BookWorkspace:
    """Atomically publish a validated Source Document and Book Workspace record.

    Inputs:
        data_root: Writable root dedicated to application data.
        source_bytes: Validated immutable PDF bytes.
        filename: Original learner-facing filename.
        source_hash: SHA-256 identity of the source bytes.
        inspection: Successful fast structural inspection.
        edition_of: Explicit prior Book Workspace identity, or None for a new lineage.
    Functionality:
        Atomically writes validated source and metadata, retains explicit edition lineage,
        and records both artifacts in the active run after publication is complete.
    Outputs:
        The public Book Workspace representation.
    Failures:
        Propagates filesystem and JSON errors; temporary files never appear as workspaces.
    """
    workspaces_root = data_root / "book-workspaces"
    workspace_root = workspaces_root / source_hash
    workspaces_root.mkdir(parents=True, exist_ok=True)
    staging_root = workspaces_root / f".{source_hash}.{uuid4()}.tmp"
    staging_root.mkdir(parents=False, exist_ok=False)

    workspace: BookWorkspace = {
        "workspace_id": source_hash,
        "source_document": {
            "filename": filename,
            "sha256": source_hash,
            "page_count": inspection["page_count"],
            "document_title": inspection["document_title"],
            "edition_of": edition_of,
            "artifact_ref": f"book-workspaces/{source_hash}/source.pdf",
        },
        "structural_scan": {"status": "complete", "headings": inspection["headings"]},
        "validation": {"outcome": "accepted", "warnings": inspection["warnings"]},
    }

    source_path = staging_root / "source.pdf"
    source_temporary = source_path.with_suffix(".pdf.tmp")
    source_temporary.write_bytes(source_bytes)
    source_temporary.replace(source_path)

    workspace_path = staging_root / "workspace.json"
    workspace_bytes = json.dumps(workspace, indent=2, sort_keys=True).encode("utf-8")
    workspace_temporary = workspace_path.with_suffix(".json.tmp")
    workspace_temporary.write_bytes(workspace_bytes)
    workspace_temporary.replace(workspace_path)

    if workspace_root.exists():
        if workspace_root.is_symlink():
            raise OSError("Refusing to replace a symbolic-link Book Workspace")
        quarantine_root = workspaces_root / ".incomplete"
        quarantine_root.mkdir(exist_ok=True)
        workspace_root.rename(quarantine_root / f"{source_hash}-{uuid4()}")
    staging_root.rename(workspace_root)

    published_source_path = workspace_root / "source.pdf"
    published_workspace_path = workspace_root / "workspace.json"
    record_artifact(published_source_path, media_type="application/pdf", sha256=source_hash)
    record_artifact(
        published_workspace_path,
        media_type="application/vnd.ai-learning.book-workspace+json",
        sha256=hashlib.sha256(workspace_bytes).hexdigest(),
    )
    return workspace


@traced
def import_source_document_content(
    *, data_root: Path, source_bytes: bytes, filename: str, edition_of: str | None = None
) -> ImportOutcome:
    """Create or reopen a content-addressed Book Workspace.

    Inputs:
        data_root: Writable root dedicated to application data.
        source_bytes: Complete PDF request body.
        filename: Original learner-facing filename.
        edition_of: Explicit prior Book Workspace identity, or None for a new lineage.
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
            "workspace": cast(
                BookWorkspace, json.loads(workspace_path.read_text(encoding="utf-8"))
            ),
        }

    if (
        edition_of is not None
        and not (data_root / "book-workspaces" / edition_of / "workspace.json").is_file()
    ):
        raise SourceRejected(
            "edition_not_found", "The selected prior Source Document edition was not found."
        )

    inspection = inspect_source_document(source_bytes)
    workspace = publish_book_workspace(
        data_root=data_root,
        source_bytes=source_bytes,
        filename=filename,
        source_hash=source_hash,
        inspection=inspection,
        edition_of=edition_of,
    )
    return {"reopened": False, "workspace": workspace}


@traced
def list_published_book_workspaces(data_root: Path) -> list[BookWorkspace]:
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
    return [
        cast(BookWorkspace, json.loads(path.read_text(encoding="utf-8")))
        for path in workspace_paths
    ]
