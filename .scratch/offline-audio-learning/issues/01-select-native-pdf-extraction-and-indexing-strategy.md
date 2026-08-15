# Select the native-PDF extraction and indexing strategy

Type: research
Status: resolved
Blocked by: none

## Question

Which native-text PDF extraction, layout analysis, chapter detection, and validation approach should the MVP adopt to preserve hierarchy, page references, paragraphs, code, tables, equations, and figures? Establish deterministic-first options, confidence and rejection signals, and implications for the Source Index using the reference book where useful.

## Answer

Adopt a deterministic, provenance-preserving pipeline using pypdf for preflight/page labels/nested outlines and pdfplumber/pdfminer.six for positioned text, typography, drawings, images, tables, and visual debugging. Make a versioned Source Index—not flattened Markdown—the canonical artifact: every typed node retains raw and reversibly normalized text, hierarchy, physical and printed pages, bounding boxes, source hashes, evidence checks, assets, and explicit warning/block states. Use tag tree → outline/bookmarks → visible-heading agreement → deterministic typography → human correction for hierarchy; reserve LLM/vision interpretation for a separate enrichment stage that never overwrites extraction.

The reference *AI Engineering* PDF is suitable for the native-text MVP and has a deep outline, but it is untagged and contains repeated footer material, MathJax Type 3 fonts, figures, and at least one visibly clipped ebook-style table. Accept it at document level while requiring targeted review of non-prose warnings. Reject corrupt/password-blocked or scan-heavy inputs; block narration on unresolved reading-order, Unicode, table, code, or equation failures. Keep PyMuPDF as a performance benchmark subject to an explicit AGPL/commercial-license decision, and Docling as a model-based escalation benchmark rather than the canonical extractor.

Full cited report: [Native-PDF extraction and Source Index strategy](../research/01-native-pdf-extraction-and-indexing.md)
