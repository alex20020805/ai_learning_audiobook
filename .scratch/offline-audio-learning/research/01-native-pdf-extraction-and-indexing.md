# Native-PDF extraction and Source Index strategy

Date: 2026-08-15

## Decision

Adopt a deterministic, provenance-preserving pipeline built around **pypdf** for PDF preflight, page labels, and nested outline/bookmark traversal, plus **pdfplumber/pdfminer.six** for page objects, characters, words, coordinates, typography, drawings, images, visual debugging, and table candidates. Both are permissively licensed (BSD-3-Clause and MIT, respectively), which avoids making an early product architecture depend on PyMuPDF's AGPL/commercial licensing. The [pypdf outline API](https://pypdf.readthedocs.io/en/stable/user/handling-outlines.html) exposes nested destinations and their zero-based target pages; [pdfplumber](https://github.com/jsvine/pdfplumber/blob/stable/README.md) is explicitly intended for machine-generated PDFs and exposes characters, lines, rectangles, curves, images, coordinates, crops, text, and table-finding/debugging operations. Its [license is MIT](https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt), while [pypdf's license is BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/main/LICENSE).

The MVP should not treat a flattened Markdown string as extraction output. It should create a **Source Index** whose nodes retain the original PDF page and geometry, raw text, normalized text, hierarchy, content type, extraction evidence, and warnings. Downstream chapter selection, episode packing, transcript generation, citations, and transformation reports must consume that index.

Do not use an LLM to recover ordinary reading order, headings, or chapter boundaries when the PDF itself provides sufficient evidence. LLM or vision-model interpretation belongs in a later, separately recorded enrichment stage and must never overwrite source extraction.

## Why PDF requires this posture

A PDF is primarily a presentation format. The pypdf maintainers document that digitally born PDFs do not store text in a semantically meaningful way and enumerate inherent ambiguities around paragraphs, headers, tables, captions, formulas, footnotes, and floating figures ([pypdf: Why text extraction is hard](https://pypdf.readthedocs.io/en/stable/user/extract-text.html#why-text-extraction-is-hard)). Author-intended reading order and semantics become predictable only when authors provide an appropriate tag tree; the PDF Association explains that Tagged PDF embeds structures such as headings, lists, tables, and figures, and cautions that layout-based recovery from an untagged file is software interpretation rather than author intent ([Tagged PDF Q&A](https://pdfa.org/resource/tagged-pdf-q-a/)).

This means “confidence” must not be a single invented probability. It should be a set of inspectable checks: whether Unicode mapped cleanly, whether an outline destination agreed with a visible heading, whether reading order was deterministic, whether a table grid was recovered, and whether a non-prose element has enough evidence to narrate.

## Proposed extraction pipeline

### 1. Immutable ingest and preflight

1. Compute a SHA-256 digest and assign `document_id`; never mutate the uploaded source.
2. Validate the PDF signature/parser open, encryption/password state, page count, page boxes, rotations, page labels, metadata, outlines, and tag-tree presence.
3. Inventory embedded text, fonts/encodings, raster images, and vector drawings on every selected page. Sample across the whole document for the initial whole-book plan; do not assess only the first pages.
4. Classify pages as `native_text`, `blank`, `front_matter`, `figure_dominant`, `scan_suspected`, or `extraction_failed` using evidence, while leaving ambiguous pages as `unknown`.

Reject corrupted or password-blocked files. Reject as outside the native-text MVP when more than 10% of nonblank pages in the selected learning span are scan-suspected—defined initially as fewer than 20 printable embedded characters combined with a raster image covering more than half the page. Exclude cover, intentionally blank, and verified figure-only pages from that ratio. Make the threshold configurable and calibrate it on the pilot corpus rather than presenting it as a universal truth.

### 2. Extract source primitives, not prose alone

For each page, retain character/word/line candidates with coordinates and typography before grouping. `pdfminer.six`, on which pdfplumber is built, can expose exact location, font, and color from the PDF source ([pdfminer.six project documentation](https://github.com/pdfminer/pdfminer.six)). pdfplumber exposes object-level character, line, rectangle, curve, and image dictionaries, crops, and page-relative/document-relative coordinates ([pdfplumber object model](https://github.com/jsvine/pdfplumber/blob/stable/README.md#objects)).

Build blocks using a fixed, versioned set of spacing and alignment rules. Preserve both:

- `raw_text`: character sequence from the chosen reading-order grouping;
- `normalized_text`: reversible cleanup only—Unicode normalization, soft-hyphen repair, line-wrap dehyphenation, and whitespace repair—with an operation log.

Never silently remove content. Repeated headers, footers, page numbers, or watermarks become `page_furniture` nodes after cross-page frequency and positional checks; they are excluded from narration by policy but remain traceable in the Source Index and transformation report.

### 3. Recover hierarchy in an evidence order

Use the following priority:

1. **Tag tree**, when present and internally consistent.
2. **Nested PDF outline/bookmarks**, mapping every destination to physical page and target coordinate when available. pypdf represents children as nested lists and resolves each destination to its page ([pypdf outline documentation](https://pypdf.readthedocs.io/en/stable/user/handling-outlines.html#reading-pdf-outlines)).
3. **Visible heading agreement**, locating the outline title near its destination and using its typography to refine exact start coordinates.
4. **Deterministic typography fallback** when no usable outline exists: repeated font-family/size/weight roles, whitespace, numbering patterns, short-line shape, and agreement with any printed table of contents.
5. **Human correction** in the chapter-boundary screen.

An outline is evidence, not truth: warn on destinations outside the file, decreasing page order among sibling chapters, duplicate titles/destinations, or failure to find a similar visible heading near the target. Do not promote a typography candidate to a chapter merely because it is large or bold; require a consistent document-wide role or user confirmation.

### 4. Preserve non-prose as typed source nodes

- **Code:** detect primarily from monospaced font spans, indentation, line density, and surrounding labels such as “Example,” not syntax guessed by an LLM. Preserve exact line breaks, spacing, page crop, and language as `unknown` unless explicit evidence identifies it. Never paragraph-reflow code.
- **Tables:** run pdfplumber's table finder and preserve cell grid, bounding box, raw text, caption, and page crop. Its documented algorithm derives candidate cell boundaries from explicit or word-alignment-implied lines and exposes tables, rows, columns, cells, and bounding boxes ([pdfplumber table extraction](https://github.com/jsvine/pdfplumber/blob/stable/README.md#extracting-tables)). If the grid is incomplete, overlapping, or disagrees materially with the page text, mark `needs_review`; do not invent headers or cells.
- **Equations:** retain extracted glyph sequence, fonts, baselines/superscript evidence, bounding box, and rendered crop. A formula is `narration_blocked` if it contains replacement characters, anomalous controls, severe overlap, or cannot be reconstructed from its visual layout. The faithful pipeline may say that an equation on a named page needs viewing; a later interpretation model can add a clearly separated explanation.
- **Figures:** inventory both raster images and vector drawings, associate nearby numbered captions deterministically, and store a page crop. Raster-image enumeration alone is insufficient because charts and diagrams may be vector graphics; PyMuPDF's own documentation makes the same distinction ([PyMuPDF image/vector note](https://github.com/pymupdf/PyMuPDF)). Extraction should not claim to understand what the figure means.
- **Lists, callouts, and footnotes:** preserve them as distinct nodes. Link footnote markers to notes only when marker/text evidence is unambiguous; otherwise retain page-local order and warn.

### 5. Validate before index publication

Run deterministic checks at document, page, hierarchy, and node levels:

- text round-trip counts and raw-text hashes;
- Unicode replacement-character and unexpected-control-character ratios;
- impossible/out-of-page bounding boxes, overlapping duplicate glyphs, or repeated text layers;
- line/column ordering discontinuities and block crossings;
- outline-to-heading agreement;
- repeated-furniture classification frequency;
- unpaired captions, unindexed large images/drawing regions, and table/equation/code blocks without a typed node;
- empty or implausibly short content spans between adjacent outline destinations;
- source coverage: every narratable character belongs to one source node, and every excluded character belongs to an explicitly typed excluded node.

Initial stop rules for a selected span:

- **Hard reject:** unreadable/corrupt PDF, unavailable decryption, or scan-heavy threshold exceeded.
- **Block generation:** extraction failure on any selected content page; more than 0.5% Unicode replacement characters in prose; an unresolved reading-order conflict spanning more than one prose block; or an unresolved equation/table/code item whose surrounding prose depends on it.
- **Warn and require targeted review:** outline mismatch, isolated low-confidence glyphs, an unmatched caption, repeated-layer suspicion, or a visual node that can safely be called out without explaining it.

The percentages are provisional pilot guardrails. Record the raw metrics so they can be tuned against observed false accepts and false rejects.

## Source Index contract

Use a versioned JSON/SQLite representation with this logical shape:

```text
Document
  document_id, source_sha256, page_count, metadata
  extractor_versions, extractor_config, created_at
  page_labels[], outline[], validation_summary

SourceNode
  node_id, parent_id, order, hierarchy_path
  type: chapter | section | paragraph | list | list_item | code |
        table | equation | figure | caption | footnote | callout |
        page_furniture | unknown
  raw_text, normalized_text, normalization_operations[]
  source_spans[]:
    physical_page_index, physical_page_number, printed_page_label,
    bbox, character_range, raw_text_sha256
  assets[]: page_crop | raster_image | rendered_region
  evidence:
    hierarchy_source, font_roles, outline_destination, caption_link
  checks:
    unicode, reading_order, classification, structure, source_coverage
  status: accepted | warning | needs_review | narration_blocked
  warnings[]
```

`node_id` should be reproducible from document digest, physical page, normalized bounding boxes, content type, and raw-text hash. Store physical page index and printed page label separately; never overload “page number.” A normalized paragraph spanning pages should contain multiple `source_spans`, so the transcript can cite the exact page(s) and crop without searching the PDF again.

The learning plan and episode packer should reference node IDs and ranges, not copy source text into topic folders. Generated scripts, audio, quiz evidence, and learner memory may point back to those stable IDs. Re-extraction under a new parser version creates a new Source Index version and an explicit mapping/diff; it must not silently move existing citations.

## Reference-book inspection: *AI Engineering*

Non-destructive local inspection of the user's file on 2026-08-15 found:

- 991 letter-sized pages, PDF 1.4, unencrypted, created by calibre 7.4.0;
- embedded Unicode-mapped CID TrueType fonts and extractable prose, so it fits the native-text MVP;
- `Tagged: no`, so no author-provided semantic tag tree;
- a deep `/Outlines` tree with chapter, section, and subsection destinations, including chapter-level destinations and target coordinates—excellent primary evidence for chapter boundaries;
- Liberation Mono fonts for code-like material and MathJax Type 3 fonts for mathematical material, supporting typed detection but requiring equation checks;
- repeated site/footer text that should be classified as page furniture rather than narrated;
- raster and illustrated figures with numbered captions;
- an ebook-style table on physical page 146 whose visible last-column heading is clipped and whose frame includes a horizontal scrollbar. Plain extraction yielded the clipped heading while the numeric cells remained visible. This is a source-layout defect, not something a parser or LLM should silently “repair.” It should produce a table warning and page crop for review.

Accordingly, this book should be accepted at document level, with its PDF outline driving the initial Source Index. It should not be auto-cleared wholesale: table, equation, figure, and code nodes must be inspected across representative chapters, and each detected source defect must remain visible in the transformation report.

## Alternatives considered

### PyMuPDF as the primary parser

PyMuPDF offers attractive high-speed block/word extraction, bounding boxes, sorting, image/vector information, outlines, and table finding. Its documentation notes that plain extraction may not match natural reading order even when coordinate sorting is requested ([PyMuPDF text extraction details](https://pymupdf.readthedocs.io/en/latest/app1.html)). It is a good benchmark or replaceable adapter if performance becomes unacceptable. However, its repository is licensed under the [GNU AGPL](https://github.com/pymupdf/PyMuPDF/blob/main/COPYING) with commercial licensing available, which creates an avoidable product/distribution decision for a private-web-app architecture. Do not adopt it as the default without an explicit licensing decision; this is not legal advice.

### Docling as the primary representation

Docling's unified document model can represent text, tables, pictures, hierarchy, bounding boxes, provenance, furniture, and reading order ([DoclingDocument concepts](https://github.com/docling-project/docling/blob/main/docs/concepts/docling_document.md)). Its PDF pipeline uses specialized layout and table-structure models ([Docling technical report](https://arxiv.org/abs/2408.09869)). That makes it promising as a benchmark or escalation path for complex pages, but it adds model inference and a larger abstraction at the stage where the faithful MVP benefits from deterministic evidence and transparent failure. Do not make its inferred structure canonical; compare it on the pilot only when the deterministic pipeline raises a warning.

### Flat `pdftotext`/Markdown extraction

Useful as an independent smoke-test and diff oracle, but insufficient as the Source Index because it loses stable object identity, geometry, typed visual nodes, and the evidence needed for page-level citations and transformation reports.

## Pilot acceptance tests for this decision

Before locking implementation, run the stack on three manually chosen spans from *AI Engineering*:

1. prose with nested headings and footnotes;
2. code and/or MathJax equations;
3. a figure and a table, including the clipped table around physical page 146.

For each span, compare the rendered page, raw primitives, Source Index, and generated source transcript. Pass only if hierarchy and reading order are correct, every substantive source element is represented, exclusions are explicit, page/crop links resolve, and ambiguous visual material blocks or warns rather than being guessed. Also time a whole-book indexing run and measure peak memory; only revisit PyMuPDF/Docling if pdfplumber's one-time cost is operationally unacceptable.

## Consequences for later tickets

- Episode packing should operate on accepted SourceNodes and may not cut within code, table, equation, figure/caption, list, or unresolved argument groups.
- Faithful narration transformations must produce a node-level diff against `normalized_text` and must preserve SourceNode citations.
- Visual explanation and personalized examples are enrichment artifacts with their own source/model provenance, never fields that overwrite source nodes.
- The chapter-confirmation UI should show outline-derived boundaries, printed/physical pages, warnings, and rendered crops for affected nodes.
- A model comparison should evaluate only uncertain classification or later rewriting/explanation; native extraction quality is tested independently of Qwen/hosted LLM quality.
