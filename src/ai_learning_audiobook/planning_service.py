"""Chapter inspection, scoped Source Index extraction, and Episode planning."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from statistics import median
from typing import Any, TypedDict, cast

import pdfplumber
from pypdf import PdfReader

from ai_learning_audiobook.import_service import BookWorkspace
from ai_learning_audiobook.tracing import current_run, record_artifact, traced

WORD_PATTERN = re.compile(r"[\w]+(?:['’.-][\w]+)*", re.UNICODE)
WORKSPACE_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SOURCE_INDEX_SCHEMA_VERSION = "1"
PLANNING_SCHEMA_VERSION = "1"
ESTIMATED_WORDS_PER_MINUTE = 150.0


class PlanningRejected(Exception):
    """Carry a stable public rejection for chapter planning."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Create one actionable planning rejection.

        Inputs:
            code: Stable machine-readable error code.
            message: Learner-facing explanation.
            status_code: HTTP status appropriate for the domain failure.
            details: Optional structured evidence safe to expose locally.
        Functionality:
            Retains the public failure contract while behaving as a normal exception.
        Outputs:
            None; initializes this exception instance.
        Failures:
            Does not raise for valid constructor values.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class DurationPolicy(TypedDict):
    """Validated Book Workspace duration policy."""

    minimum_minutes: float
    maximum_minutes: float
    target_minutes: float
    version: str


class ChapterCatalog(TypedDict):
    """Inspectable chapter candidates and page-boundary evidence."""

    workspace_id: str
    chapters: list[dict[str, Any]]


class PlanningOutcome(TypedDict):
    """Public result of extracting and planning one confirmed source span."""

    workspace_id: str
    source_index: dict[str, Any]
    plan: dict[str, Any]


@traced
def stable_json_hash(value: object) -> str:
    """Hash one JSON-compatible value using a canonical representation.

    Inputs:
        value: JSON-compatible value whose identity must be stable.
    Functionality:
        Serializes with sorted keys and compact separators before SHA-256 hashing.
    Outputs:
        Lowercase hexadecimal SHA-256 digest.
    Failures:
        Propagates JSON serialization errors for unsupported values.
    """
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


@traced
def load_book_workspace(data_root: Path, workspace_id: str) -> BookWorkspace:
    """Load one published Book Workspace through a path-safe identifier.

    Inputs:
        data_root: Application data root.
        workspace_id: Exact lowercase SHA-256 workspace identifier.
    Functionality:
        Rejects unsafe identifiers and reads the published workspace record.
    Outputs:
        Parsed BookWorkspace mapping.
    Failures:
        Raises PlanningRejected with `workspace_not_found` when unavailable or unsafe.
    """
    if not WORKSPACE_ID_PATTERN.fullmatch(workspace_id):
        raise PlanningRejected(
            "workspace_not_found", "The selected Book Workspace was not found.", status_code=404
        )
    workspace_path = data_root / "book-workspaces" / workspace_id / "workspace.json"
    if not workspace_path.is_file():
        raise PlanningRejected(
            "workspace_not_found", "The selected Book Workspace was not found.", status_code=404
        )
    return cast(BookWorkspace, json.loads(workspace_path.read_text(encoding="utf-8")))


@traced
def bounded_page_preview(text: str) -> dict[str, Any]:
    """Represent a page with bounded beginning and ending sentence evidence.

    Inputs:
        text: Native text extracted from one physical PDF page.
    Functionality:
        Collapses display whitespace and retains short beginning/end excerpts plus a hash.
    Outputs:
        Preview mapping with character count, hash, beginning, and ending text.
    Failures:
        Does not raise for valid Python strings.
    """
    compact = " ".join(text.split())
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]
    beginning_sentence = next((sentence for sentence in sentences if len(sentence) >= 20), None)
    beginning = (beginning_sentence or (sentences[0] if sentences else compact))[:240]
    ending = (sentences[-1] if sentences else compact)[-240:]
    return {
        "character_count": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "beginning": beginning,
        "ending": ending,
    }


@traced
def inspect_chapter_catalog(data_root: Path, workspace_id: str) -> ChapterCatalog:
    """Expose detected chapters with adjacent context and boundary previews.

    Inputs:
        data_root: Application data root.
        workspace_id: Published Book Workspace identity.
    Functionality:
        Resolves suggested chapter ends, neighboring headings, printed/physical pages, and
        bounded first/last-page previews without performing detailed extraction.
    Outputs:
        ChapterCatalog ordered by detected source position.
    Failures:
        Raises PlanningRejected for an unknown workspace or unreadable retained source.
    """
    workspace = load_book_workspace(data_root, workspace_id)
    workspace_root = data_root / "book-workspaces" / workspace_id
    source_path = workspace_root / "source.pdf"
    try:
        reader = PdfReader(source_path)
        page_labels = reader.page_labels
    except (OSError, ValueError) as error:
        raise PlanningRejected(
            "source_unavailable", "The retained Source Document could not be inspected."
        ) from error

    headings = sorted(
        workspace["structural_scan"]["headings"],
        key=lambda heading: int(heading["physical_page_number"]),
    )
    page_count = int(workspace["source_document"]["page_count"])
    chapters: list[dict[str, Any]] = []
    for index, heading in enumerate(headings):
        start_page = int(heading["physical_page_number"])
        next_start = (
            int(headings[index + 1]["physical_page_number"])
            if index + 1 < len(headings)
            else page_count + 1
        )
        end_page = max(start_page, next_start - 1)
        first_text = reader.pages[start_page - 1].extract_text() or ""
        last_text = reader.pages[end_page - 1].extract_text() or ""
        chapters.append(
            {
                "heading_index": index,
                "title": heading["title"],
                "suggested_span": {
                    "start_physical_page": start_page,
                    "end_physical_page": end_page,
                    "start_printed_page": page_labels[start_page - 1],
                    "end_printed_page": page_labels[end_page - 1],
                },
                "previous_heading": headings[index - 1] if index > 0 else None,
                "next_heading": headings[index + 1] if index + 1 < len(headings) else None,
                "first_page_preview": bounded_page_preview(first_text),
                "last_page_preview": bounded_page_preview(last_text),
                "evidence": heading["evidence"],
            }
        )
    return {"workspace_id": workspace_id, "chapters": chapters}


@traced
def validate_duration_policy(minimum_minutes: float, maximum_minutes: float) -> DurationPolicy:
    """Validate and version one Book Workspace duration policy.

    Inputs:
        minimum_minutes: Requested lower Episode bound.
        maximum_minutes: Requested upper Episode bound.
    Functionality:
        Enforces finite values, pilot bounds, a strict ordering, and a five-to-ten-minute
        policy width; derives the midpoint target and content-addressed version.
    Outputs:
        Validated DurationPolicy.
    Failures:
        Raises PlanningRejected with `invalid_duration_policy` for unsupported bounds.
    """
    values = (minimum_minutes, maximum_minutes)
    valid = (
        all(math.isfinite(value) for value in values)
        and 5 <= minimum_minutes < maximum_minutes <= 30
        and 5 <= maximum_minutes - minimum_minutes <= 10
    )
    if not valid:
        raise PlanningRejected(
            "invalid_duration_policy",
            "Duration policy must satisfy 5 <= minimum < maximum <= 30 and span 5–10 minutes.",
        )
    target = (minimum_minutes + maximum_minutes) / 2
    identity = {
        "minimum_minutes": minimum_minutes,
        "maximum_minutes": maximum_minutes,
        "target_minutes": target,
    }
    return {
        "minimum_minutes": minimum_minutes,
        "maximum_minutes": maximum_minutes,
        "target_minutes": target,
        "version": stable_json_hash(identity),
    }


@traced
def normalize_source_text(raw_text: str) -> tuple[str, list[dict[str, str]]]:
    """Apply only reversible, explicitly recorded source-text normalization.

    Inputs:
        raw_text: Extracted block text in observed line order.
    Functionality:
        Normalizes Unicode composition, joins discretionary line-break hyphens, and collapses
        whitespace while recording each operation that changes the value.
    Outputs:
        Normalized text and ordered transformation-operation records.
    Failures:
        Does not raise for valid Python strings.
    """
    value = raw_text
    operations: list[dict[str, str]] = []
    normalized_unicode = unicodedata.normalize("NFC", value)
    if normalized_unicode != value:
        operations.append({"operation": "unicode_nfc", "reason": "canonical composition"})
        value = normalized_unicode
    dehyphenated = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", value)
    if dehyphenated != value:
        operations.append(
            {"operation": "join_line_break_hyphen", "reason": "reversible PDF line wrap"}
        )
        value = dehyphenated
    collapsed = " ".join(value.split())
    if collapsed != value:
        operations.append({"operation": "collapse_whitespace", "reason": "spoken text form"})
        value = collapsed
    return value, operations


@traced
def classify_source_node(text: str, *, maximum_font_size: float, median_font_size: float) -> str:
    """Assign a conservative typed-node label from observable text/layout signals.

    Inputs:
        text: Raw extracted block text.
        maximum_font_size: Largest word font size in the block.
        median_font_size: Median word font size on the physical page.
    Functionality:
        Detects captions, code, equations, tables, notes, callouts, and headings using explicit
        patterns; falls back to paragraph instead of inventing semantic meaning.
    Outputs:
        Stable source-node type string.
    Failures:
        Does not raise for valid strings and finite font sizes.
    """
    stripped = text.strip()
    lowered = stripped.casefold()
    if re.match(r"^(figure|fig\.)\s+\d", lowered):
        return "caption"
    if re.match(r"^table\s+\d", lowered) or "\t" in stripped:
        return "table"
    if re.search(r"(^|\n)\s*(def |class |return |assert |for |while |import )", stripped):
        return "code"
    if re.search(r"[=∑∏√≤≥]|\b(equation|perplexity|entropy)\b", lowered):
        return "equation"
    if re.match(r"^(note|warning|tip)\s*[:.]", lowered):
        return "note"
    if re.match(r"^(sidebar|callout)\s*[:.]", lowered):
        return "callout"
    if maximum_font_size >= median_font_size + 2 or re.match(
        r"^(?:chapter\s+)?\d+(?:\.\d+)*[\s.:–—-]", stripped, re.I
    ):
        return "heading"
    return "paragraph"


@traced
def group_page_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group positioned PDF words into conservative atomic text blocks.

    Inputs:
        words: pdfplumber word mappings in observed text-flow order.
    Functionality:
        Groups nearby words into lines, then uses vertical gaps and heading typography to form
        blocks that are never split by Ticket 02 packing.
    Outputs:
        Ordered block mappings containing text, bounding box, and font evidence.
    Failures:
        Raises KeyError or numeric conversion errors for malformed extractor output.
    """
    if not words:
        return []
    page_font_sizes = [float(word.get("size", 0.0)) for word in words]
    page_median = median(page_font_sizes) if page_font_sizes else 0.0
    lines: list[dict[str, Any]] = []
    for word in words:
        top = float(word["top"])
        if not lines or abs(top - float(lines[-1]["top"])) > 3:
            lines.append(
                {
                    "top": top,
                    "bottom": float(word["bottom"]),
                    "x0": float(word["x0"]),
                    "x1": float(word["x1"]),
                    "words": [str(word["text"])],
                    "font_sizes": [float(word.get("size", 0.0))],
                }
            )
        else:
            line = lines[-1]
            line["bottom"] = max(float(line["bottom"]), float(word["bottom"]))
            line["x0"] = min(float(line["x0"]), float(word["x0"]))
            line["x1"] = max(float(line["x1"]), float(word["x1"]))
            cast(list[str], line["words"]).append(str(word["text"]))
            cast(list[float], line["font_sizes"]).append(float(word.get("size", 0.0)))

    blocks: list[dict[str, Any]] = []
    for line in lines:
        line_text = " ".join(cast(list[str], line["words"]))
        line_maximum = max(cast(list[float], line["font_sizes"]), default=0.0)
        line_is_heading = (
            classify_source_node(
                line_text, maximum_font_size=line_maximum, median_font_size=page_median
            )
            == "heading"
        )
        previous = blocks[-1] if blocks else None
        vertical_gap = (
            float(line["top"]) - float(previous["bottom"]) if previous is not None else 0.0
        )
        starts_block = previous is None or line_is_heading or bool(previous["is_heading"])
        starts_block = starts_block or vertical_gap > max(9.0, page_median * 0.9)
        if starts_block:
            blocks.append(
                {
                    "lines": [line_text],
                    "top": line["top"],
                    "bottom": line["bottom"],
                    "x0": line["x0"],
                    "x1": line["x1"],
                    "font_sizes": list(cast(list[float], line["font_sizes"])),
                    "median_font_size": page_median,
                    "is_heading": line_is_heading,
                }
            )
        else:
            block = blocks[-1]
            cast(list[str], block["lines"]).append(line_text)
            block["bottom"] = max(float(block["bottom"]), float(line["bottom"]))
            block["x0"] = min(float(block["x0"]), float(line["x0"]))
            block["x1"] = max(float(block["x1"]), float(line["x1"]))
            cast(list[float], block["font_sizes"]).extend(cast(list[float], line["font_sizes"]))
    return blocks


@traced
def extract_source_index(
    data_root: Path,
    workspace_id: str,
    *,
    selected_title: str,
    start_physical_page: int,
    end_physical_page: int,
) -> dict[str, Any]:
    """Extract a provenance-preserving Source Index for exactly one confirmed span.

    Inputs:
        data_root: Application data root.
        workspace_id: Published Book Workspace identity.
        selected_title: Learner-selected chapter heading.
        start_physical_page: Inclusive one-based extraction start.
        end_physical_page: Inclusive one-based extraction end.
    Functionality:
        Reads only selected PDF pages, groups positioned text into typed atomic nodes, records
        normalization/evidence/warnings, and computes stable node and index hashes.
    Outputs:
        Source Index mapping ready for durable publication and packing.
    Failures:
        Raises PlanningRejected when the confirmed span has no substantive native text;
        propagates unexpected PDF layout errors.
    """
    workspace = load_book_workspace(data_root, workspace_id)
    source_path = data_root / "book-workspaces" / workspace_id / "source.pdf"
    reader = PdfReader(source_path)
    page_labels = reader.page_labels
    nodes: list[dict[str, Any]] = []
    index_warnings: list[dict[str, Any]] = []
    hierarchy_path = [selected_title]
    with pdfplumber.open(source_path) as document:
        for page_number in range(start_physical_page, end_physical_page + 1):
            page = document.pages[page_number - 1]
            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False,
                extra_attrs=["fontname", "size"],
            )
            blocks = group_page_words(words)
            if not blocks:
                index_warnings.append(
                    {
                        "code": "blank_page",
                        "severity": "informational",
                        "physical_page_number": page_number,
                        "printed_page_label": page_labels[page_number - 1],
                        "message": "No narratable native text was found on this page.",
                    }
                )
                continue
            for block_order, block in enumerate(blocks):
                raw_text = "\n".join(cast(list[str], block["lines"]))
                normalized_text, operations = normalize_source_text(raw_text)
                font_sizes = cast(list[float], block["font_sizes"])
                node_type = classify_source_node(
                    raw_text,
                    maximum_font_size=max(font_sizes, default=0.0),
                    median_font_size=float(block["median_font_size"]),
                )
                node_warnings: list[dict[str, str]] = []
                if "�" in raw_text:
                    node_warnings.append(
                        {
                            "code": "unreadable_replacement_character",
                            "severity": "blocking",
                            "message": (
                                "Extracted text contains an unreadable replacement character."
                            ),
                        }
                    )
                elif any(marker in raw_text for marker in ("Â", "Ã")):
                    node_warnings.append(
                        {
                            "code": "suspected_text_corruption",
                            "severity": "review_required",
                            "message": "Extracted text contains a possible encoding artifact.",
                        }
                    )
                if node_type == "heading":
                    hierarchy_path = [selected_title, normalized_text]
                word_count = len(WORD_PATTERN.findall(normalized_text))
                identity = {
                    "workspace_id": workspace_id,
                    "physical_page_number": page_number,
                    "block_order": block_order,
                    "raw_text": raw_text,
                    "geometry": {
                        "x0": round(float(block["x0"]), 3),
                        "top": round(float(block["top"]), 3),
                        "x1": round(float(block["x1"]), 3),
                        "bottom": round(float(block["bottom"]), 3),
                    },
                }
                node_id = stable_json_hash(identity)
                node = {
                    "node_id": node_id,
                    "type": node_type,
                    "hierarchy_path": list(hierarchy_path),
                    "raw_text": raw_text,
                    "normalized_text": normalized_text,
                    "normalization_operations": operations,
                    "page_references": [
                        {
                            "physical_page_number": page_number,
                            "printed_page_label": page_labels[page_number - 1],
                        }
                    ],
                    "geometry": identity["geometry"],
                    "evidence": {
                        "method": "pdfplumber_positioned_words",
                        "source_order": len(nodes),
                        "font_size_min": min(font_sizes, default=0.0),
                        "font_size_max": max(font_sizes, default=0.0),
                    },
                    "warnings": node_warnings,
                    "word_count": word_count,
                    "estimated_minutes": word_count / ESTIMATED_WORDS_PER_MINUTE,
                    "atomic": True,
                }
                node["sha256"] = stable_json_hash(node)
                nodes.append(node)
                index_warnings.extend(
                    {
                        **warning,
                        "node_id": node_id,
                        "physical_page_number": page_number,
                        "printed_page_label": page_labels[page_number - 1],
                    }
                    for warning in node_warnings
                )
    if not nodes or sum(int(node["word_count"]) for node in nodes) == 0:
        raise PlanningRejected(
            "empty_confirmed_span", "The confirmed span contains no substantive native text."
        )
    source_identity = {
        "schema_version": SOURCE_INDEX_SCHEMA_VERSION,
        "workspace_id": workspace_id,
        "source_sha256": workspace["source_document"]["sha256"],
        "span": {
            "start_physical_page": start_physical_page,
            "end_physical_page": end_physical_page,
        },
        "node_hashes": [node["sha256"] for node in nodes],
        "warnings": index_warnings,
    }
    source_index_hash = stable_json_hash(source_identity)
    return {
        **source_identity,
        "source_index_id": source_index_hash,
        "sha256": source_index_hash,
        "artifact_ref": (f"book-workspaces/{workspace_id}/source-indexes/{source_index_hash}.json"),
        "nodes": nodes,
    }


@traced
def pack_source_nodes(
    source_index: dict[str, Any], duration_policy: DurationPolicy, *, approve_short_tail: bool
) -> dict[str, Any]:
    """Pack contiguous atomic nodes into a duration-bounded provisional Learning Plan.

    Inputs:
        source_index: Ordered confirmed-span Source Index.
        duration_policy: Validated Book Workspace duration policy.
        approve_short_tail: Whether the exact proposed final short tail is approved.
    Functionality:
        Uses dynamic programming to minimize target-duration distance while preferring
        hierarchy boundaries, never splits a node, exposes provisional cuts, and blocks
        indivisible units above the policy maximum or the hard thirty-minute ceiling.
    Outputs:
        Versioned plan mapping with ordered Listening Sessions and explicit approval state.
    Failures:
        Does not raise for a structurally valid Source Index; blocking outcomes are returned.
    """
    nodes = cast(list[dict[str, Any]], source_index["nodes"])
    durations = [float(node["estimated_minutes"]) for node in nodes]
    hard_overlong = [node for node, duration in zip(nodes, durations, strict=True) if duration > 30]
    policy_overlong = [
        node
        for node, duration in zip(nodes, durations, strict=True)
        if duration > duration_policy["maximum_minutes"]
    ]
    plan_identity = {
        "schema_version": PLANNING_SCHEMA_VERSION,
        "source_index_sha256": source_index["sha256"],
        "duration_policy": duration_policy,
    }
    if hard_overlong or policy_overlong:
        blocked = hard_overlong or policy_overlong
        return {
            **plan_identity,
            "plan_id": stable_json_hash({**plan_identity, "status": "blocked_source_structure"}),
            "status": "blocked_source_structure",
            "listening_sessions": [],
            "blocked_atomic_units": [
                {
                    "node_id": node["node_id"],
                    "estimated_minutes": node["estimated_minutes"],
                    "page_references": node["page_references"],
                    "reason": "Atomic source unit exceeds the allowed Episode duration.",
                    "hard_ceiling_exceeded": float(node["estimated_minutes"]) > 30,
                }
                for node in blocked
            ],
            "short_tail_approval": None,
        }

    prefix = [0.0]
    for duration in durations:
        prefix.append(prefix[-1] + duration)
    decisions: list[dict[str, Any] | None] = [None] * (len(nodes) + 1)
    decisions[0] = {"cost": 0.0, "previous": None}
    for end in range(1, len(nodes) + 1):
        for start in range(end - 1, -1, -1):
            duration = prefix[end] - prefix[start]
            if duration > duration_policy["maximum_minutes"]:
                break
            prior = decisions[start]
            if prior is None or duration < duration_policy["minimum_minutes"]:
                continue
            next_node = nodes[end] if end < len(nodes) else None
            hierarchy_boundary = next_node is None or next_node["type"] == "heading"
            boundary_penalty = 0.0 if hierarchy_boundary else 2.0
            cost = (
                float(prior["cost"])
                + (duration - duration_policy["target_minutes"]) ** 2
                + boundary_penalty
            )
            if decisions[end] is None or cost < float(cast(dict[str, Any], decisions[end])["cost"]):
                decisions[end] = {
                    "cost": cost,
                    "previous": start,
                    "duration": duration,
                    "short_tail": False,
                }

    if decisions[-1] is None:
        end = len(nodes)
        for start in range(end - 1, -1, -1):
            prior = decisions[start]
            if prior is None:
                continue
            duration = prefix[end] - prefix[start]
            if not 0 < duration < duration_policy["minimum_minutes"]:
                continue
            cost = float(prior["cost"]) + 100 + (duration_policy["minimum_minutes"] - duration) ** 2
            if decisions[end] is None or cost < float(cast(dict[str, Any], decisions[end])["cost"]):
                decisions[end] = {
                    "cost": cost,
                    "previous": start,
                    "duration": duration,
                    "short_tail": True,
                }

    if decisions[-1] is None:
        return {
            **plan_identity,
            "plan_id": stable_json_hash({**plan_identity, "status": "blocked_source_structure"}),
            "status": "blocked_source_structure",
            "listening_sessions": [],
            "blocked_atomic_units": [],
            "short_tail_approval": None,
            "reason": "No contiguous atomic partition satisfies the selected duration policy.",
        }

    selections: list[dict[str, Any]] = []
    cursor = len(nodes)
    while cursor > 0:
        decision = cast(dict[str, Any], decisions[cursor])
        start = int(decision["previous"])
        selections.append({**decision, "start": start, "end": cursor})
        cursor = start
    selections.reverse()
    sessions: list[dict[str, Any]] = []
    for number, selection in enumerate(selections, start=1):
        selected = nodes[int(selection["start"]) : int(selection["end"])]
        next_node = nodes[int(selection["end"])] if int(selection["end"]) < len(nodes) else None
        hierarchy_boundary = next_node is None or next_node["type"] == "heading"
        sessions.append(
            {
                "session_number": number,
                "node_ids": [node["node_id"] for node in selected],
                "start_physical_page": selected[0]["page_references"][0]["physical_page_number"],
                "end_physical_page": selected[-1]["page_references"][-1]["physical_page_number"],
                "estimated_minutes": selection["duration"],
                "word_count": sum(int(node["word_count"]) for node in selected),
                "status": "short_tail" if selection.get("short_tail") else "planned",
                "boundary": "hierarchy" if hierarchy_boundary else "provisional_semantic",
                "cuts_atomic_unit": False,
            }
        )
    short_tail = next((session for session in sessions if session["status"] == "short_tail"), None)
    status = "confirmed"
    approval: dict[str, Any] | None = None
    if short_tail is not None:
        approval = {
            "required": True,
            "approved": approve_short_tail,
            "pages": {
                "start_physical_page": short_tail["start_physical_page"],
                "end_physical_page": short_tail["end_physical_page"],
            },
            "reason": "No all-valid partition exists without this final semantic tail.",
            "revised_plan_length": len(sessions),
            "estimated_incremental_cost_usd": 0.0,
            "cost_basis": "No paid provider route is selected in Ticket 02.",
        }
        if not approve_short_tail:
            status = "awaiting_short_tail_approval"
    complete_identity = {**plan_identity, "sessions": sessions, "approval": approval}
    return {
        **complete_identity,
        "plan_id": stable_json_hash({**complete_identity, "status": status}),
        "status": status,
        "listening_sessions": sessions,
        "blocked_atomic_units": [],
        "short_tail_approval": approval,
    }


@traced
def atomic_write_json(path: Path, value: object) -> str:
    """Atomically write a JSON artifact and return its content digest.

    Inputs:
        path: Final durable artifact path.
        value: JSON-compatible artifact value.
    Functionality:
        Creates parent directories, writes a sibling temporary file, and replaces the final
        path so readers never observe a partial JSON document.
    Outputs:
        SHA-256 digest of the exact persisted bytes.
    Failures:
        Propagates filesystem and JSON serialization failures.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    return hashlib.sha256(encoded).hexdigest()


@traced
def persist_planning_outcome(
    data_root: Path, workspace_id: str, source_index: dict[str, Any], plan: dict[str, Any]
) -> None:
    """Persist immutable extraction/plan artifacts and update current planning state.

    Inputs:
        data_root: Application data root.
        workspace_id: Published Book Workspace identity.
        source_index: Content-addressed detailed extraction artifact.
        plan: Content-addressed provisional or confirmed Learning Plan.
    Functionality:
        Writes immutable artifacts idempotently, records them in the active trace, and updates
        a replace-safe state pointer without mutating prior plans or duration policies.
    Outputs:
        None.
    Failures:
        Propagates filesystem and JSON serialization failures.
    """
    workspace_root = data_root / "book-workspaces" / workspace_id
    index_path = workspace_root / "source-indexes" / f"{source_index['source_index_id']}.json"
    plan_path = workspace_root / "plans" / f"{plan['plan_id']}.json"
    index_digest = atomic_write_json(index_path, source_index)
    plan_digest = atomic_write_json(plan_path, plan)
    state_path = workspace_root / "planning-state.json"
    prior_state = (
        cast(dict[str, Any], json.loads(state_path.read_text(encoding="utf-8")))
        if state_path.is_file()
        else {"schema_version": PLANNING_SCHEMA_VERSION, "plan_ids": []}
    )
    plan_ids = list(cast(list[str], prior_state.get("plan_ids", [])))
    if plan["plan_id"] not in plan_ids:
        plan_ids.append(cast(str, plan["plan_id"]))
    state = {
        "schema_version": PLANNING_SCHEMA_VERSION,
        "current_duration_policy": plan["duration_policy"],
        "latest_plan_id": plan["plan_id"],
        "plan_ids": plan_ids,
    }
    state_digest = atomic_write_json(state_path, state)
    record_artifact(
        index_path,
        media_type="application/vnd.ai-learning.source-index+json",
        sha256=index_digest,
    )
    record_artifact(
        plan_path,
        media_type="application/vnd.ai-learning.plan+json",
        sha256=plan_digest,
    )
    record_artifact(
        state_path,
        media_type="application/vnd.ai-learning.planning-state+json",
        sha256=state_digest,
    )


@traced
def confirm_chapter_plan(
    data_root: Path,
    workspace_id: str,
    *,
    heading_index: int,
    start_physical_page: int,
    end_physical_page: int,
    minimum_minutes: float = 15.0,
    maximum_minutes: float = 25.0,
    allow_cross_chapter: bool = False,
    approve_short_tail: bool = False,
    boundary_note: str = "",
) -> PlanningOutcome:
    """Confirm a chapter span, extract it, and create a provisional Learning Plan.

    Inputs:
        data_root: Application data root.
        workspace_id: Published Book Workspace identity.
        heading_index: Zero-based selected detected heading.
        start_physical_page: Inclusive adjusted one-based start page.
        end_physical_page: Inclusive adjusted one-based end page.
        minimum_minutes: Requested Episode lower duration bound.
        maximum_minutes: Requested Episode upper duration bound.
        allow_cross_chapter: Whether the confirmed span may pass the next detected heading.
        approve_short_tail: Approval for the exact returned final-tail proposal.
        boundary_note: Optional learner rationale retained with the selection.
    Functionality:
        Validates selection and policy, limits detailed extraction to the confirmed pages,
        packs atomic nodes, records boundary evidence, and persists immutable versions.
    Outputs:
        PlanningOutcome containing the Source Index and Learning Plan.
    Failures:
        Raises PlanningRejected for invalid identifiers, heading selection, span, or policy.
    """
    workspace = load_book_workspace(data_root, workspace_id)
    catalog = inspect_chapter_catalog(data_root, workspace_id)
    chapters = catalog["chapters"]
    if heading_index < 0 or heading_index >= len(chapters):
        raise PlanningRejected("invalid_heading", "Select one detected Source Chapter.")
    page_count = int(workspace["source_document"]["page_count"])
    if not (1 <= start_physical_page <= end_physical_page <= page_count):
        raise PlanningRejected(
            "invalid_span", f"Source span must be within physical pages 1–{page_count}."
        )
    selected = chapters[heading_index]
    suggested = cast(dict[str, Any], selected["suggested_span"])
    suggested_start = int(suggested["start_physical_page"])
    suggested_end = int(suggested["end_physical_page"])
    if end_physical_page < suggested_start or start_physical_page > suggested_end:
        raise PlanningRejected(
            "selected_heading_outside_span",
            "The confirmed span must overlap the selected detected chapter.",
        )
    if not allow_cross_chapter and end_physical_page > suggested_end:
        raise PlanningRejected(
            "cross_chapter_not_allowed",
            "Enable chapter crossing before extending beyond the detected chapter end.",
        )
    policy = validate_duration_policy(minimum_minutes, maximum_minutes)
    source_index = extract_source_index(
        data_root,
        workspace_id,
        selected_title=str(selected["title"]),
        start_physical_page=start_physical_page,
        end_physical_page=end_physical_page,
    )
    plan = pack_source_nodes(source_index, policy, approve_short_tail=approve_short_tail)
    plan["selection"] = {
        "heading_index": heading_index,
        "title": selected["title"],
        "confirmed_span": {
            "start_physical_page": start_physical_page,
            "end_physical_page": end_physical_page,
        },
        "suggested_span": suggested,
        "allow_cross_chapter": allow_cross_chapter,
        "boundary_note": boundary_note,
        "evidence": selected["evidence"],
    }
    plan["plan_id"] = stable_json_hash(
        {key: value for key, value in plan.items() if key != "plan_id"}
    )
    persist_planning_outcome(data_root, workspace_id, source_index, plan)
    current_run().record(
        "validation_completed",
        outcome=plan["status"],
        plan_id=plan["plan_id"],
        source_index_sha256=source_index["sha256"],
    )
    return {"workspace_id": workspace_id, "source_index": source_index, "plan": plan}


@traced
def read_planning_state(data_root: Path, workspace_id: str) -> dict[str, Any]:
    """Read current planning state and every retained immutable plan summary.

    Inputs:
        data_root: Application data root.
        workspace_id: Published Book Workspace identity.
    Functionality:
        Validates the workspace, reads its state pointer, and loads referenced plans in order.
    Outputs:
        Mapping containing current duration policy, latest plan, and retained plan history.
    Failures:
        Raises PlanningRejected when the workspace or planning state is unavailable;
        propagates JSON errors for corrupt retained artifacts.
    """
    load_book_workspace(data_root, workspace_id)
    workspace_root = data_root / "book-workspaces" / workspace_id
    state_path = workspace_root / "planning-state.json"
    if not state_path.is_file():
        raise PlanningRejected(
            "planning_not_started", "No chapter span has been confirmed yet.", status_code=404
        )
    state = cast(dict[str, Any], json.loads(state_path.read_text(encoding="utf-8")))
    plans = [
        json.loads((workspace_root / "plans" / f"{plan_id}.json").read_text(encoding="utf-8"))
        for plan_id in cast(list[str], state["plan_ids"])
    ]
    return {"workspace_id": workspace_id, "state": state, "plans": plans}
