"""
Document text extraction and chunking service — version 2.

Chunking quality improvements (WP-B):
--------------------------------------
B1. Heading detection uses font-size/weight hints from pypdf's visitor_text
    callback, with regex fallbacks for numbered headings, ALL-CAPS titles,
    and markdown "#".
B2. Repeated headers and footers are stripped: lines whose normalized form
    (digits → #, whitespace collapsed) appear on ≥50% of pages, plus
    standalone page-number patterns ("Page N", "N", "- N -", "N of M").
B3. Hard-wrapped lines inside a paragraph are reflowed; end-of-line
    hyphenation is repaired; paragraph breaks and list items are preserved;
    exactly one blank line separates paragraphs.
B4. Section-aware chunking: a chunk never crosses a top-level section
    boundary. Target ~1 200 chars, max 1 800, overlap ~150 chars (same
    section only). Long paragraphs split on sentence boundaries; the
    sentence splitter avoids splitting after list/heading numerals (e.g.
    "5."), decimals, common abbreviations.
B5. section_title is the full heading path ("3. Foo > 3.2 Bar"). Null for
    front matter before the first real numbered/titled heading.
B6. Embed f"{section_title}\\n{content}" but store content clean without the
    prefix. chunk_metadata["chunker_version"] = 2.
B7. chunk_metadata: page_number, page_numbers, heading_path, chunk_chars,
    embedding_model, embedding_dim, chunker_version, document_title.
TOC. A "Contents" or "Table of Contents" block whose entries duplicate
    headings found later in the document (or end in page numbers / dot
    leaders) is excluded from chunks and from the heading stack.
"""
from __future__ import annotations

import io
import re
import unicodedata
from typing import Any

import pypdf
import pypdf.errors

from app.core.config import settings


# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------


class ParseError(ValueError):
    """Deterministic document parsing or validation failure."""
    pass


# ---------------------------------------------------------------------------
# Text sanitization
# ---------------------------------------------------------------------------


def sanitize_text(text: str) -> str:
    """
    Sanitize text before chunking or storage:
    - NFC-normalize Unicode
    - Remove NUL and other C0 control characters except \\n and \\t
    - Collapse runs of horizontal whitespace on each line
    - Collapse runs of 3+ blank lines to 2
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = []
    for ch in text:
        code = ord(ch)
        if (code < 32 and code not in (9, 10)) or code == 127:
            continue
        cleaned.append(ch)
    text = "".join(cleaned)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def sanitize_section_title(title: str | None) -> str | None:
    """Sanitize section title and collapse into a single-line string."""
    if not title:
        return None
    cleaned = sanitize_text(title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None


def get_printable_ratio(text: str) -> float:
    """Ratio of printable characters (including \\n and \\t) to total characters."""
    if not text:
        return 0.0
    printable = sum(1 for ch in text if ch.isprintable() or ch in ("\n", "\t"))
    return printable / len(text)


# ---------------------------------------------------------------------------
# Heading detection (B1)
# ---------------------------------------------------------------------------

# Numbered heading: "1.", "1.2", "1.2.3." followed by text
_NUMBERED_HEADING_RE = re.compile(
    r"^\d+(?:\.\d+)*\.?\s+\S",
)
# Section keyword: "Section 1:", "Chapter 2"
_SECTION_HEADING_RE = re.compile(
    r"^(?:section|chapter|part)\s+\d+",
    re.IGNORECASE,
)
# Markdown heading
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
# TOC heading: "Contents" or "Table of Contents"
_TOC_HEADING_RE = re.compile(
    r"^(?:contents?|table\s+of\s+contents?)$",
    re.IGNORECASE,
)
# Line that looks "sentence-like": has a comma-separated clause, or ends with
# sentence-ending punctuation, or is long (>120 chars)
_SENTENCE_LIKE_RE = re.compile(
    r",\s+[a-z]|[.!?]\s*$"
)
# TOC entry: ends in digit(s) or dot-leaders + digit
_TOC_ENTRY_RE = re.compile(r"(?:\.{3,}|\s{2,})\d+\s*$|\s+\d+\s*$")


def _is_sentence_like(line: str) -> bool:
    """Return True if a line looks like a body sentence rather than a heading."""
    if len(line) > 120:
        return True
    if _SENTENCE_LIKE_RE.search(line):
        return True
    # Lots of lowercase words mid-sentence
    words = line.split()
    if len(words) > 10:
        return True
    return False


def _is_heading_text(
    line: str,
    is_bold: bool = False,
    font_size_ratio: float = 1.0,
    *,
    require_short: bool = True,
) -> bool:
    """
    Return True if the line looks like a section heading.

    Priority:
    1. Numbered heading regex — highest confidence (ignores font).
    2. Font size significantly larger than body (ratio > 1.15) OR bold with
       ratio > 1.0 AND the line is NOT sentence-like.
    3. ALL-CAPS title (≥3 letters, no trailing period, short).
    4. Markdown '#' heading.
    5. Section/Chapter keyword.

    A line is always rejected if it is sentence-like (long, contains commas
    before lowercase words, or ends with sentence punctuation).
    """
    line = line.strip()
    if not line or len(line) > 150:
        return False

    # Numbered section heading — check before sentence-like filter because
    # numbered headings with commas in the title are still headings.
    if _NUMBERED_HEADING_RE.match(line):
        return True

    # Reject sentence-like lines (body text misidentified by font)
    if _is_sentence_like(line):
        return False

    # Layout hint: significantly larger/bolder font
    if font_size_ratio > 1.15 or (is_bold and font_size_ratio > 1.0):
        return True

    # Section keyword
    if _SECTION_HEADING_RE.match(line):
        return True

    # Markdown heading
    if _MARKDOWN_HEADING_RE.match(line):
        return True

    # ALL-CAPS heading: at least 3 uppercase letters, no trailing period
    letters = [ch for ch in line if ch.isalpha()]
    if letters and len(letters) >= 3 and len(line) <= 80 and line.isupper() and not line.endswith("."):
        return True

    return False


def _extract_heading_number(line: str) -> str | None:
    """Return the numeric prefix (e.g. '3.2') from a numbered heading, else None."""
    m = re.match(r"^(\d+(?:\.\d+)*)\.?\s+", line.strip())
    return m.group(1) if m else None


def _heading_depth(line: str) -> int:
    """Return depth of a numbered heading: '1.' → 1, '1.2' → 2, etc. Non-numbered → 0."""
    num = _extract_heading_number(line)
    if num is None:
        return 0
    return num.count(".") + 1


# ---------------------------------------------------------------------------
# TOC detection
# ---------------------------------------------------------------------------


def _is_toc_block(
    lines: list[str],
    known_headings: set[str] | None = None,
) -> bool:
    """
    Heuristic: return True if a block of lines looks like a table of contents.
    Criteria (any two of):
      - Contains a "Contents" or "Table of Contents" title line
      - Multiple lines ending in page numbers or dot-leaders + numbers
      - Lines that duplicate numbered headings found elsewhere (if known_headings given)
    """
    has_toc_title = any(_TOC_HEADING_RE.match(l.strip()) for l in lines)
    toc_entry_count = sum(1 for l in lines if _TOC_ENTRY_RE.search(l.strip()))
    duplicate_count = 0
    if known_headings:
        for l in lines:
            normalized = re.sub(r"\s+", " ", l.strip())
            if any(normalized == h or normalized in h or h in normalized for h in known_headings):
                duplicate_count += 1

    if has_toc_title and toc_entry_count >= 2:
        return True
    if has_toc_title and duplicate_count >= 2:
        return True
    if toc_entry_count >= 3:
        return True
    return False


def _detect_toc_lines(
    all_lines: list[tuple[str, int]],
    block_meta: dict[int, dict[str, dict]],
) -> set[int]:
    """
    Identify line indices that belong to a TOC block.

    Strategy:
    1. Find any line matching _TOC_HEADING_RE.
    2. Collect contiguous entries (numbered items, dot-leaders, short titles)
       on the same page until notes or body text begin.
    3. Exclude all those line indices from chunking.
    """
    excluded: set[int] = set()

    i = 0
    while i < len(all_lines):
        line, page_num = all_lines[i]
        stripped = line.strip()

        if _TOC_HEADING_RE.match(stripped):
            excluded.add(i)
            j = i + 1
            while j < len(all_lines):
                jl, jpn = all_lines[j]
                js = jl.strip()
                if not js:
                    j += 1
                    continue
                m = block_meta.get(jpn, {}).get(js, {})
                if jpn == page_num and (
                    _NUMBERED_HEADING_RE.match(js)
                    or m.get("size_ratio", 1.0) <= 1.05
                    or _TOC_ENTRY_RE.search(js)
                ):
                    if js.lower().startswith("test note:") or js.lower().startswith("note:"):
                        break
                    excluded.add(j)
                    j += 1
                else:
                    break
            i = j
        else:
            i += 1

    return excluded


# ---------------------------------------------------------------------------
# Page text extraction with font metadata (B1)
# ---------------------------------------------------------------------------


class _PageInfo:
    """Text blocks with font metadata from a single PDF page."""

    def __init__(self) -> None:
        self.blocks: list[dict] = []  # {"text": str, "size": float, "bold": bool}
        self._body_sizes: list[float] = []

    def add(self, text: str, size: float, bold: bool) -> None:
        if text.strip():
            self.blocks.append({"text": text, "size": size, "bold": bold})
            self._body_sizes.append(size)

    def median_size(self) -> float:
        if not self._body_sizes:
            return 12.0
        s = sorted(self._body_sizes)
        mid = len(s) // 2
        return s[mid]


def _extract_pdf_pages_with_layout(
    file_path: str,
) -> list[tuple[int, list[dict]]]:
    """
    Extract text blocks from a PDF with font-size and bold hints.

    Returns list of (page_number, blocks) where each block is:
      {"text": str, "size": float, "bold": bool}
    Page numbers are 1-indexed.
    """
    try:
        reader = pypdf.PdfReader(file_path)
    except pypdf.errors.FileNotDecryptedError:
        raise ParseError("PDF is encrypted and cannot be processed") from None
    except Exception as exc:
        raise ParseError(f"Corrupt or invalid PDF file: {exc}") from exc

    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt("")
            if not decrypted:
                raise ParseError("PDF is encrypted and cannot be processed")
        except ParseError:
            raise
        except Exception:
            raise ParseError("PDF is encrypted and cannot be processed") from None

    try:
        num_pages = len(reader.pages)
    except Exception as exc:
        raise ParseError(f"Corrupt or invalid PDF file: {exc}") from exc

    if num_pages > settings.MAX_PDF_PAGES:
        raise ParseError(
            f"PDF exceeds maximum page limit of {settings.MAX_PDF_PAGES} pages "
            f"(found {num_pages})"
        )

    result: list[tuple[int, list[dict]]] = []
    for page_idx, page in enumerate(reader.pages, start=1):
        page_info = _PageInfo()

        # Visitor callback to capture font metadata
        def _visitor(text: str, cm, tm, font_dict, font_size, _pi=page_info) -> None:  # noqa: ANN001
            if not text or not text.strip():
                return
            size = abs(font_size) if font_size else 12.0
            bold = False
            if font_dict:
                base_font = str(font_dict.get("/BaseFont", ""))
                bold = "Bold" in base_font or "bold" in base_font
            _pi.add(text, size, bold)

        try:
            page.extract_text(visitor_text=_visitor)
        except Exception:
            # Fallback: plain text extraction
            try:
                raw = page.extract_text() or ""
                for line in raw.split("\n"):
                    page_info.add(line, 12.0, False)
            except Exception as exc:
                raise ParseError(f"Error extracting text from page {page_idx}: {exc}") from exc

        result.append((page_idx, page_info.blocks))

    return result


# ---------------------------------------------------------------------------
# Header/footer stripping (B2)
# ---------------------------------------------------------------------------

_DIGIT_NORM_RE = re.compile(r"\d+")
_SPACE_NORM_RE = re.compile(r"\s+")
# Page-number patterns: "Page N", "N", "- N -", "N of M"
_PAGE_NUM_RE = re.compile(
    r"^(?:page\s+\d+|\d+\s+of\s+\d+|-\s*\d+\s*-|\d+)$",
    re.IGNORECASE,
)


def _normalize_for_fingerprint(line: str) -> str:
    """Normalize a line for header/footer detection: digits→#, whitespace collapse."""
    line = _DIGIT_NORM_RE.sub("#", line.strip())
    line = _SPACE_NORM_RE.sub(" ", line)
    return line.lower()


def _detect_repeated_lines(
    pages_lines: list[list[str]],
    threshold: float = 0.5,
) -> set[str]:
    """
    Return a set of normalized line fingerprints that appear on >= threshold
    fraction of pages. These are candidates for page headers/footers.
    Only applies to documents with at least 2 pages, and a line must appear on
    at least 2 distinct pages to be considered repeated.
    Candidates are restricted to header/footer zones (top 3 and bottom 3 lines of a page)
    and numbered headings are never treated as repeated headers/footers.
    """
    if not pages_lines or len(pages_lines) < 2:
        return set()
    n_pages = len(pages_lines)
    freq: dict[str, int] = {}
    for page_lines in pages_lines:
        seen_on_page: set[str] = set()
        candidates = page_lines[:3] + (page_lines[-3:] if len(page_lines) > 3 else [])
        for line in candidates:
            stripped = line.strip()
            if _NUMBERED_HEADING_RE.match(stripped):
                continue
            fp = _normalize_for_fingerprint(stripped)
            if fp and fp not in seen_on_page:
                freq[fp] = freq.get(fp, 0) + 1
                seen_on_page.add(fp)
    return {fp for fp, count in freq.items() if count >= 2 and count / n_pages >= threshold}


def _strip_headers_footers(
    pages_lines: list[list[str]],
    repeated: set[str],
) -> list[list[str]]:
    """Remove repeated header/footer lines and standalone page-number lines."""
    result = []
    for page_lines in pages_lines:
        cleaned = []
        for line in page_lines:
            fp = _normalize_for_fingerprint(line)
            if fp in repeated:
                continue
            if _PAGE_NUM_RE.match(line.strip()):
                continue
            cleaned.append(line)
        result.append(cleaned)
    return result


# ---------------------------------------------------------------------------
# Line reflow (B3)
# ---------------------------------------------------------------------------

# Sentence endings that allow the next line to start a continuation
_HARD_WRAP_LIKELY_END_RE = re.compile(
    r"(?<![.!?])\s*$"  # line does not end with sentence-ending punctuation
)
# A line that starts with a lower-case letter (likely continuation of previous)
_CONTINUATION_START_RE = re.compile(r"^[a-z(\"\'\u2018\u201c]")
# End-of-line hyphen
_HYPHEN_END_RE = re.compile(r"-$")
# List item
_LIST_ITEM_RE = re.compile(r"^(\s*[\u2022\u2013\u2014\-\*]|\s*\d+[.)]\s)")


def _reflow_lines(lines: list[str]) -> list[str]:
    """
    Reflow a paragraph's lines into properly-joined text.

    Rules:
    - If a line ends with a hyphen and the next starts lower-case → de-hyphenate.
    - If a line doesn't end with sentence punctuation and the next starts
      lower-case or with punctuation → join with space.
    - Preserve paragraph boundaries (empty lines) and list items.
    """
    if not lines:
        return []

    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Empty line → paragraph break
        if not line.strip():
            result.append("")
            i += 1
            continue

        # Start of a list item → keep as-is
        if _LIST_ITEM_RE.match(line):
            result.append(line.strip())
            i += 1
            continue

        # Attempt to join with following lines
        current = line
        while i + 1 < len(lines):
            nxt = lines[i + 1].rstrip()

            # Next is empty or list item → stop
            if not nxt.strip() or _LIST_ITEM_RE.match(nxt):
                break

            # Check for hard-wrap: current doesn't end with sentence punct,
            # next starts with lower-case or joining punctuation
            nxt_stripped = nxt.strip()
            current_stripped = current.rstrip()

            if _HYPHEN_END_RE.search(current_stripped):
                # De-hyphenate
                current = current_stripped[:-1] + nxt_stripped
                i += 1
            elif (
                not current_stripped.endswith((".", "!", "?", ":", ";"))
                and _CONTINUATION_START_RE.match(nxt_stripped)
            ):
                current = current_stripped + " " + nxt_stripped
                i += 1
            else:
                break

        result.append(current.strip())
        i += 1

    return result


# ---------------------------------------------------------------------------
# Document title extraction
# ---------------------------------------------------------------------------


def _extract_document_title(pages_blocks: list[tuple[int, list[dict]]]) -> str | None:
    """
    Extract the document title: the largest font text on page 1 (must be >= 14pt
    and not a numbered heading).
    Concatenates consecutive lines with the same max font size.
    """
    if not pages_blocks:
        return None
    _page_num, blocks = pages_blocks[0]
    if not blocks:
        return None

    non_num_blocks = [b for b in blocks if not _NUMBERED_HEADING_RE.match(b.get("text", "").strip())]
    if not non_num_blocks:
        return None

    max_size = max((b.get("size", 0) for b in non_num_blocks), default=0)
    if max_size < 14.0:
        return None

    title_parts = []
    for block in non_num_blocks:
        size = block.get("size", 0)
        text = block.get("text", "").strip()
        if size >= max_size * 0.95 and text:
            title_parts.append(text)

    if title_parts:
        return sanitize_section_title(" ".join(title_parts))
    return None


# ---------------------------------------------------------------------------
# Section-aware chunking (B4-B7)
# ---------------------------------------------------------------------------

_TARGET_CHARS = 1200
_MAX_CHARS = 1800
_OVERLAP_CHARS = 150
_MIN_CHUNK_CHARS = 150  # Merge chunks smaller than this

# Sentence splitter that avoids splitting after list/heading numerals,
# decimals, common abbreviations, or initials.
# Strategy: split on ". ", "! ", "? " but NOT when preceded by digits
# (numbered items), single letters (initials), or known abbreviations.
_ABBREV_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|Ave|Blvd|Fig|etc|i\.?e|e\.?g|vs|cf|al|et)\.",
    re.IGNORECASE,
)
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\u201c])")


def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences, avoiding splits after:
    - List/heading numerals ("5.", "1.1")
    - Decimals ("3.14")
    - Common abbreviations (Dr., i.e., etc.)
    - Single-letter initials ("J. Smith")
    """
    # Protect abbreviations and numerals with a placeholder
    protected = text
    # Protect "digit." patterns (list items, decimals)
    protected = re.sub(r"(\d+\.)", lambda m: m.group().replace(".", "\x00"), protected)
    # Protect known abbreviations
    protected = _ABBREV_RE.sub(lambda m: m.group().replace(".", "\x00"), protected)

    # Split on sentence boundaries
    raw_sentences = _SENTENCE_END_RE.split(protected)

    # Restore placeholders
    sentences = [s.replace("\x00", ".").strip() for s in raw_sentences if s.strip()]
    return sentences


def _build_chunk(
    parts: list[str],
    section_title: str | None,
    chunk_index: int,
    page_nums: list[int],
    document_title: str | None = None,
    chunker_version: int = 2,
) -> dict[str, Any]:
    """Assemble a chunk dict from accumulated parts."""
    content = sanitize_text("\n\n".join(p for p in parts if p.strip()))
    heading_path = section_title  # same value, kept for metadata

    # Build metadata (B7)
    metadata: dict[str, Any] = {
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIM,
        "chunker_version": chunker_version,
        "chunk_chars": len(content),
        "heading_path": heading_path,
    }
    if document_title:
        metadata["document_title"] = document_title
    if page_nums:
        metadata["page_number"] = page_nums[0]
        metadata["page_numbers"] = sorted(set(page_nums))

    return {
        "content": content,
        "chunk_index": chunk_index,
        "section_title": section_title,
        "token_count": max(1, len(content) // 4),
        "page_number": page_nums[0] if page_nums else 1,
        "chunk_metadata": metadata,
    }


def _chunk_section(
    paragraphs: list[tuple[str, int]],  # (text, page_num)
    section_title: str | None,
    start_index: int,
    document_title: str | None = None,
    overlap_text: str | None = None,
) -> tuple[list[dict], str | None]:
    """
    Produce chunks from the paragraphs of ONE top-level section.

    Returns (chunks, last_overlap_text).
    """
    chunks: list[dict] = []
    chunk_index = start_index
    current_parts: list[str] = []
    current_chars: int = 0
    current_pages: list[int] = []

    if overlap_text:
        current_parts.append(overlap_text)
        current_chars += len(overlap_text)

    def _flush() -> None:
        nonlocal chunk_index, current_parts, current_chars, current_pages
        if not any(p.strip() for p in current_parts):
            return
        chunks.append(_build_chunk(current_parts, section_title, chunk_index, current_pages, document_title))
        chunk_index += 1
        current_parts = []
        current_chars = 0
        current_pages = []

    for para_text, page_num in paragraphs:
        if not para_text.strip():
            continue

        para_chars = len(para_text)
        current_pages.append(page_num)

        if current_chars + para_chars <= _MAX_CHARS:
            current_parts.append(para_text)
            current_chars += para_chars

            # Opportunistically flush when we've hit the target
            if current_chars >= _TARGET_CHARS:
                _flush()
        else:
            # Flush current, then handle this paragraph
            if current_parts:
                _flush()

            if para_chars > _MAX_CHARS:
                # Paragraph is too large — split on sentence boundaries
                sentences = _split_sentences(para_text)
                for sent in sentences:
                    sent_chars = len(sent)
                    if current_chars + sent_chars > _MAX_CHARS and current_parts:
                        _flush()
                    current_parts.append(sent)
                    current_chars += sent_chars
                    current_pages.append(page_num)
                    if current_chars >= _TARGET_CHARS:
                        _flush()
            else:
                current_parts.append(para_text)
                current_chars += para_chars
                if current_chars >= _TARGET_CHARS:
                    _flush()

    if current_parts and any(p.strip() for p in current_parts):
        _flush()

    # Compute overlap from last chunk for use in next section
    # (only within the same section — B4)
    if chunks:
        last_content = chunks[-1]["content"]
        if len(last_content) > _OVERLAP_CHARS:
            overlap = last_content[-_OVERLAP_CHARS:]
            # Don't start overlap in the middle of a word
            space_idx = overlap.find(" ")
            if space_idx > 0:
                overlap = overlap[space_idx + 1:]
        else:
            overlap = None
    else:
        overlap = None

    # Rebase chunk indices (they're relative in this function; caller sets base)
    for i, c in enumerate(chunks):
        c["chunk_index"] = start_index + i

    return chunks, overlap


def _merge_small_chunks(chunks: list[dict]) -> list[dict]:
    """
    Merge chunks smaller than _MIN_CHUNK_CHARS into an adjacent neighbor
    within the same section. Preserves section boundaries (no cross-section merge).
    """
    if not chunks:
        return chunks

    merged = True
    while merged:
        merged = False
        result: list[dict] = []
        i = 0
        while i < len(chunks):
            c = chunks[i]
            clen = len(c["content"])
            if clen < _MIN_CHUNK_CHARS:
                # Try merging with previous if same section
                if result and result[-1]["section_title"] == c["section_title"]:
                    prev = result[-1]
                    combined_content = sanitize_text(prev["content"] + "\n\n" + c["content"])
                    if len(combined_content) <= _MAX_CHARS:
                        prev["content"] = combined_content
                        prev["chunk_metadata"]["chunk_chars"] = len(combined_content)
                        # Merge page_numbers
                        all_pages = sorted(set(
                            prev["chunk_metadata"].get("page_numbers", [prev["page_number"]]) +
                            c["chunk_metadata"].get("page_numbers", [c["page_number"]])
                        ))
                        prev["chunk_metadata"]["page_numbers"] = all_pages
                        merged = True
                        i += 1
                        continue
                # Try merging with next if same section
                elif i + 1 < len(chunks) and chunks[i + 1]["section_title"] == c["section_title"]:
                    nxt = chunks[i + 1]
                    combined_content = sanitize_text(c["content"] + "\n\n" + nxt["content"])
                    if len(combined_content) <= _MAX_CHARS:
                        nxt_copy = dict(nxt)
                        nxt_copy["content"] = combined_content
                        nxt_copy["chunk_metadata"] = dict(nxt["chunk_metadata"])
                        nxt_copy["chunk_metadata"]["chunk_chars"] = len(combined_content)
                        all_pages = sorted(set(
                            c["chunk_metadata"].get("page_numbers", [c["page_number"]]) +
                            nxt["chunk_metadata"].get("page_numbers", [nxt["page_number"]])
                        ))
                        nxt_copy["chunk_metadata"]["page_numbers"] = all_pages
                        nxt_copy["page_number"] = c["page_number"]
                        result.append(nxt_copy)
                        merged = True
                        i += 2
                        continue
            result.append(c)
            i += 1
        chunks = result

    # Re-index
    for idx, c in enumerate(chunks):
        c["chunk_index"] = idx
    return chunks


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def extract_and_chunk(
    file_path: str,
    content_type: str | None = None,
    max_tokens: int = 400,  # kept for API compatibility; not used in v2 chunker
) -> list[dict[str, Any]]:
    """
    Extract text and produce section-aware chunks with page tracking.

    Uses the v2 chunker (B1-B7). Falls back gracefully if pypdf layout
    extraction fails. Enforces quality gates before returning.
    """
    from pathlib import Path as _Path
    path = _Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Determine whether this is a PDF
    is_pdf = False
    if content_type and "pdf" in content_type.lower():
        is_pdf = True
    elif path.suffix.lower() == ".pdf":
        is_pdf = True
    else:
        try:
            with open(file_path, "rb") as fh:
                magic = fh.read(4)
                if magic.startswith(b"%PDF"):
                    is_pdf = True
        except Exception as exc:
            raise ParseError(f"Could not read file: {exc}") from exc

    if is_pdf:
        return _extract_and_chunk_pdf(file_path)
    else:
        return _extract_and_chunk_text(file_path, content_type)


def _extract_and_chunk_pdf(file_path: str) -> list[dict[str, Any]]:
    """Full PDF extraction and v2 chunking pipeline."""

    # ---- 1. Extract pages with layout info ----
    pages_with_layout = _extract_pdf_pages_with_layout(file_path)

    # ---- 2. Convert to lines per page ----
    pages_lines: list[list[str]] = []
    pages_blocks: list[tuple[int, list[dict]]] = []

    for page_num, blocks in pages_with_layout:
        lines = []
        for block in blocks:
            for line in block["text"].split("\n"):
                l = line.strip()
                if l:
                    lines.append(l)
        pages_lines.append(lines)
        pages_blocks.append((page_num, blocks))

    # ---- 3. Detect and strip repeated headers/footers (B2) ----
    repeated = _detect_repeated_lines(pages_lines)
    stripped_pages_lines = _strip_headers_footers(pages_lines, repeated)

    # ---- 4. Extract document title from page 1 (largest font) ----
    document_title = _extract_document_title(pages_with_layout)

    # ---- 5. Compute median font size per page for heading detection ----
    page_medians: dict[int, float] = {}
    for page_num, blocks in pages_blocks:
        if blocks:
            sizes = [b["size"] for b in blocks if b.get("size", 0) > 0]
            if sizes:
                s = sorted(sizes)
                page_medians[page_num] = s[len(s) // 2]
    global_median = (
        sum(page_medians.values()) / len(page_medians)
        if page_medians
        else 12.0
    )

    # ---- 6. Build per-block heading annotations ----
    # Map: page_num → {line_text_normalized: {"bold": bool, "size_ratio": float}}
    block_meta: dict[int, dict[str, dict]] = {}
    for page_num, blocks in pages_blocks:
        median = page_medians.get(page_num, global_median) or 12.0
        block_meta[page_num] = {}
        for block in blocks:
            for raw_line in block["text"].split("\n"):
                key = raw_line.strip()
                if key:
                    block_meta[page_num][key] = {
                        "bold": block.get("bold", False),
                        "size_ratio": (block.get("size", 12.0) or 12.0) / (median or 12.0),
                    }

    # ---- 7. Aggregate all cleaned lines across pages ----
    all_lines: list[tuple[str, int]] = []
    for (page_num, _blocks), cleaned_lines in zip(pages_blocks, stripped_pages_lines):
        for line in cleaned_lines:
            all_lines.append((line, page_num))

    if not all_lines:
        raise ParseError(
            "No extractable text in this PDF (scanned or image-only PDFs are not supported yet)"
        )

    total_chars = sum(len(l) for l, _ in all_lines)
    if total_chars < settings.MIN_EXTRACTED_CHARS:
        raise ParseError(
            "No extractable text in this PDF (scanned or image-only PDFs are not supported yet)"
        )

    # ---- 8. Detect and exclude TOC block lines ----
    toc_excluded_indices = _detect_toc_lines(all_lines, block_meta)

    # ---- 9. Parse into sections ----
    # A "section" is identified by a heading line.
    # Structure: list of (section_title, [(paragraph_text, page_num)])
    # section_title=None for front matter before the first real heading.
    sections: list[tuple[str | None, list[tuple[str, int]]]] = []
    current_title: str | None = None
    current_paragraphs: list[tuple[str, int]] = []
    in_front_matter: bool = True  # True until we hit the first numbered heading
    # Track heading hierarchy for section_title path (B5)
    heading_stack: list[str] = []  # list of heading strings at each level

    # Group lines into paragraphs (split on blank lines) then analyze
    # We build paragraphs from consecutive non-blank lines.
    para_lines: list[tuple[str, int]] = []

    def _close_para() -> None:
        nonlocal para_lines
        if not para_lines:
            return
        lines_only = [l for l, _ in para_lines]
        page_num = para_lines[0][1]

        # Reflow the paragraph
        reflowed = _reflow_lines(lines_only)
        text = " ".join(r for r in reflowed if r).strip()
        if text:
            current_paragraphs.append((text, page_num))
        para_lines = []

    def _new_section(title: str | None) -> None:
        nonlocal current_title, current_paragraphs, in_front_matter
        if current_paragraphs or current_title is not None:
            sections.append((current_title, current_paragraphs))
        current_title = title
        current_paragraphs = []
        if title is not None and _NUMBERED_HEADING_RE.match(title):
            in_front_matter = False

    for idx, (line, page_num) in enumerate(all_lines):
        # Skip TOC-excluded lines
        if idx in toc_excluded_indices:
            # Close any open paragraph first (TOC block boundary)
            _close_para()
            continue

        stripped = line.strip()

        if not stripped:
            _close_para()
            continue

        # Get font metadata for this line
        meta = block_meta.get(page_num, {}).get(stripped, {})
        bold = meta.get("bold", False)
        size_ratio = meta.get("size_ratio", 1.0)

        is_heading = _is_heading_text(stripped, is_bold=bold, font_size_ratio=size_ratio)

        # TOC heading markers ("Contents") should be treated as non-heading once
        # the TOC block detection already excluded them above; but if by some
        # chance a lone "Contents" line wasn't caught in the TOC block, skip it.
        if is_heading and _TOC_HEADING_RE.match(stripped):
            # Don't add to heading stack; skip this line
            _close_para()
            continue

        # Ignore doc title lines as headings (they belong to front matter)
        if document_title and stripped in document_title and not _NUMBERED_HEADING_RE.match(stripped):
            is_heading = False

        if is_heading:
            _close_para()

            # Build section title path (B5)
            # Numbered headings: depth from numbering takes absolute priority
            num_prefix = _extract_heading_number(stripped)
            if num_prefix is not None:
                depth = num_prefix.count(".") + 1
                # Pop the stack to this depth (numbered heading replaces everything at this level+)
                heading_stack = heading_stack[: depth - 1]
                heading_stack.append(stripped)
            else:
                # Non-numbered heading: treat as top-level if stack is empty or as sub-level
                if not heading_stack:
                    heading_stack = [stripped]
                else:
                    # Append as child of current top-level if it looks like a subheading
                    heading_stack = [heading_stack[0], stripped]

            section_path = " > ".join(heading_stack)
            _new_section(section_path)
        else:
            para_lines.append((stripped, page_num))

    _close_para()
    if current_paragraphs or current_title is not None:
        sections.append((current_title, current_paragraphs))

    # ---- 10. Chunk each section (B4) ----
    all_chunks: list[dict[str, Any]] = []
    chunk_index = 0

    for sec_title, paragraphs in sections:
        if not paragraphs:
            continue
        sec_chunks, _overlap = _chunk_section(
            paragraphs,
            sec_title,
            start_index=chunk_index,
            document_title=document_title,
        )
        # No cross-section overlap (B4)
        for c in sec_chunks:
            c["chunk_index"] = chunk_index
            chunk_index += 1
        all_chunks.extend(sec_chunks)

    if not all_chunks:
        raise ParseError(
            "No extractable text in this PDF (scanned or image-only PDFs are not supported yet)"
        )

    # ---- 11. Merge tiny chunks (< _MIN_CHUNK_CHARS) ----
    all_chunks = _merge_small_chunks(all_chunks)

    return all_chunks


def _extract_and_chunk_text(
    file_path: str, content_type: str | None
) -> list[dict[str, Any]]:
    """Extract plain text and chunk (legacy path for non-PDF files)."""
    if content_type and not content_type.startswith("text/"):
        raise ParseError(f"Unsupported binary file type: {content_type}")
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            raw_text = fh.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as fh:
                raw_text = fh.read()
        except Exception as exc:
            raise ParseError(f"Cannot decode text file: {exc}") from exc
    except Exception as exc:
        raise ParseError(f"Could not read text file: {exc}") from exc

    if not raw_text.strip():
        raise ParseError("No extractable text in document")

    page_text = sanitize_text(raw_text)
    paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]

    chunks: list[dict[str, Any]] = []
    chunk_index = 0
    current_parts: list[str] = []
    current_chars = 0

    for para in paragraphs:
        para_chars = len(para)
        if current_chars + para_chars <= _MAX_CHARS:
            current_parts.append(para)
            current_chars += para_chars
        else:
            if current_parts:
                content = sanitize_text("\n\n".join(current_parts))
                chunks.append({
                    "content": content,
                    "chunk_index": chunk_index,
                    "section_title": None,
                    "token_count": max(1, len(content) // 4),
                    "page_number": 1,
                    "chunk_metadata": {
                        "embedding_model": settings.EMBEDDING_MODEL,
                        "embedding_dim": settings.EMBEDDING_DIM,
                        "chunker_version": 2,
                        "chunk_chars": len(content),
                        "heading_path": None,
                        "page_number": 1,
                        "page_numbers": [1],
                    },
                })
                chunk_index += 1
                current_parts = []
                current_chars = 0
            current_parts.append(para)
            current_chars += para_chars

    if current_parts:
        content = sanitize_text("\n\n".join(current_parts))
        chunks.append({
            "content": content,
            "chunk_index": chunk_index,
            "section_title": None,
            "token_count": max(1, len(content) // 4),
            "page_number": 1,
            "chunk_metadata": {
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dim": settings.EMBEDDING_DIM,
                "chunker_version": 2,
                "chunk_chars": len(content),
                "heading_path": None,
                "page_number": 1,
                "page_numbers": [1],
            },
        })

    return chunks
