"""
Upload validation — allowlist-based content sniffing and PDF structural checks.

Design
------
SUPPORTED_UPLOADS maps a sniffed MIME type to a validator callable.  Adding a
new format later means adding one entry plus a parser.  Do NOT add DOCX or any
other format now.

Validators
----------
Each validator is a callable(file_bytes: bytes) -> None that raises
UploadValidationError on failure.  The error carries an HTTP status code and
the exact JSON body the API must return.

Validation order (all checked BEFORE any side effect)
------------------------------------------------------
1. Empty file.
2. Magic bytes — first 1 024 bytes; must match the expected header.
3. Format-specific parse (PDF: pypdf off the event loop).
4. Structural checks (encrypted, page count, etc.).

Sanitising original_filename
-----------------------------
_sanitize_filename() is used to produce a safe display name stored in
Document.original_filename.  The storage key is ALWAYS "{version_id}.pdf"
and never uses the client-supplied filename.
"""
from __future__ import annotations

import io
import os
import re
import unicodedata
from typing import Callable

import pypdf
import pypdf.errors

from app.core.config import settings

# --------------------------------------------------------------------------
# Custom exception
# --------------------------------------------------------------------------


class UploadValidationError(Exception):
    """
    Raised by a validator when the file is not acceptable.

    Attributes
    ----------
    http_status : int   HTTP status code to return (400 or 413).
    error_code  : str   Machine-readable code sent in the JSON body.
    message     : str   Human-readable explanation.
    extra       : dict  Additional JSON fields to merge into the error body.
    """

    def __init__(
        self,
        http_status: int,
        error_code: str,
        message: str,
        extra: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code
        self.message = message
        self.extra = extra or {}

    def to_detail(self) -> dict:
        """Return the JSON body for FastAPI HTTPException(detail=...)."""
        return {
            "error": self.error_code,
            "message": self.message,
            **self.extra,
        }


# --------------------------------------------------------------------------
# PDF validator
# --------------------------------------------------------------------------

_PDF_MAGIC = b"%PDF-"
_SUPPORTED_TYPES_LIST = ["application/pdf"]


def validate_pdf(file_bytes: bytes) -> None:
    """
    Validate that *file_bytes* is a well-formed, non-encrypted PDF with an
    acceptable page count.

    Raises UploadValidationError with one of:
      - empty_file        (400) — zero bytes
      - invalid_file_format (400) — no %PDF- header
      - encrypted_pdf     (400) — encrypted
      - too_many_pages    (400) — exceeds MAX_PDF_PAGES
      - invalid_file_format (400) — pypdf parse failure
    """
    if not file_bytes:
        raise UploadValidationError(
            400,
            "empty_file",
            "Uploaded file is empty.",
            {"supported_types": _SUPPORTED_TYPES_LIST},
        )

    # 1. Magic bytes — read first 1 024 bytes
    if not file_bytes[:1024].lstrip().startswith(_PDF_MAGIC):
        raise UploadValidationError(
            400,
            "invalid_file_format",
            "Only PDF files are supported",
            {"supported_types": _SUPPORTED_TYPES_LIST},
        )

    # 2. Structural parse with pypdf (synchronous; caller must run off event loop)
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    except pypdf.errors.FileNotDecryptedError:
        raise UploadValidationError(
            400,
            "encrypted_pdf",
            "Encrypted PDFs are not supported. Please remove password protection before uploading.",
            {"supported_types": _SUPPORTED_TYPES_LIST},
        ) from None
    except Exception as exc:
        raise UploadValidationError(
            400,
            "invalid_file_format",
            "Only PDF files are supported",
            {"supported_types": _SUPPORTED_TYPES_LIST, "detail": str(exc)[:200]},
        ) from exc

    if reader.is_encrypted:
        # Some encrypted PDFs pass PdfReader() construction but set is_encrypted.
        try:
            result = reader.decrypt("")
            if not result:
                raise UploadValidationError(
                    400,
                    "encrypted_pdf",
                    "Encrypted PDFs are not supported. Please remove password protection before uploading.",
                    {"supported_types": _SUPPORTED_TYPES_LIST},
                )
        except UploadValidationError:
            raise
        except Exception:
            raise UploadValidationError(
                400,
                "encrypted_pdf",
                "Encrypted PDFs are not supported. Please remove password protection before uploading.",
                {"supported_types": _SUPPORTED_TYPES_LIST},
            ) from None

    try:
        num_pages = len(reader.pages)
    except Exception as exc:
        raise UploadValidationError(
            400,
            "invalid_file_format",
            "Only PDF files are supported",
            {"supported_types": _SUPPORTED_TYPES_LIST},
        ) from exc

    if num_pages == 0:
        raise UploadValidationError(
            400,
            "empty_file",
            "PDF contains no pages.",
            {"supported_types": _SUPPORTED_TYPES_LIST},
        )

    if num_pages > settings.MAX_PDF_PAGES:
        raise UploadValidationError(
            400,
            "too_many_pages",
            f"PDF has {num_pages} pages; maximum allowed is {settings.MAX_PDF_PAGES}.",
            {"supported_types": _SUPPORTED_TYPES_LIST, "max_pages": settings.MAX_PDF_PAGES},
        )


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

# SUPPORTED_UPLOADS maps sniffed MIME type to validator callable.
# To add a new format: add one entry here + one parser in services/parser.py.
# DO NOT add DOCX or any other format now.
SUPPORTED_UPLOADS: dict[str, Callable[[bytes], None]] = {
    "application/pdf": validate_pdf,
}


def sniff_content_type(file_bytes: bytes) -> str | None:
    """
    Return the sniffed MIME type from magic bytes, or None if unrecognised.

    Only returns types that are in SUPPORTED_UPLOADS.
    """
    header = file_bytes[:1024].lstrip()
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def validate_upload(file_bytes: bytes) -> str:
    """
    Validate uploaded file bytes and return the sniffed content_type.

    Raises UploadValidationError for any validation failure.
    The returned content_type is always from SUPPORTED_UPLOADS keys —
    never the client-supplied value.

    Call this function BEFORE any storage write or database insert.
    """
    if not file_bytes:
        raise UploadValidationError(
            400,
            "empty_file",
            "Uploaded file is empty.",
            {"supported_types": list(SUPPORTED_UPLOADS.keys())},
        )

    content_type = sniff_content_type(file_bytes)
    if content_type is None or content_type not in SUPPORTED_UPLOADS:
        raise UploadValidationError(
            400,
            "invalid_file_format",
            "Only PDF files are supported",
            {"supported_types": list(SUPPORTED_UPLOADS.keys())},
        )

    # Delegate to format-specific validator
    SUPPORTED_UPLOADS[content_type](file_bytes)
    return content_type


# --------------------------------------------------------------------------
# Filename sanitisation (A5)
# --------------------------------------------------------------------------

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(filename: str | None) -> str:
    """
    Return a safe display filename for storage in Document.original_filename.

    Rules (applied in order):
    1. Fallback to "document.pdf" if empty or None.
    2. Strip path separators and ".." components — take basename only.
    3. Remove NUL and other ASCII control characters (0x00-0x1F, 0x7F).
    4. NFC-normalize Unicode.
    5. Truncate to 255 characters.
    6. Fallback to "document.pdf" if result is empty after cleaning.

    The STORAGE KEY is always "{version_id}.pdf" and never uses this value.
    """
    if not filename:
        return "document.pdf"

    # Take basename only — strip any path separators from all platforms
    name = filename.replace("\\", "/")
    # Remove ".." components
    name = "/".join(part for part in name.split("/") if part not in ("", "..", "."))
    if "/" in name:
        name = name.rsplit("/", 1)[-1]

    # Strip control characters
    name = _CONTROL_RE.sub("", name)

    # NFC-normalize
    name = unicodedata.normalize("NFC", name)

    # Truncate
    name = name[:255].strip()

    return name if name else "document.pdf"
