"""Raw text extraction from PDF (PyMuPDF) and DOCX (python-docx) documents.

Raises DocumentParseError with a recruiter-friendly message for corrupted, empty,
scanned (image-only) and unsupported files.
"""
import io
import zipfile

import docx
import fitz  # PyMuPDF

SUPPORTED_TYPES = {"pdf", "docx"}
MIN_TEXT_CHARS = 50


class DocumentParseError(Exception):
    """Raised when a document cannot be turned into usable text."""

    def __init__(self, message: str, status: str = "failed"):
        super().__init__(message)
        self.status = status  # failed | unsupported


def detect_file_type(filename: str, content: bytes) -> str:
    """Determine file type from extension AND magic bytes (never trust the extension alone)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_TYPES:
        raise DocumentParseError(
            f"Unsupported file type '.{ext or '?'}'. Only PDF and DOCX are accepted.",
            status="unsupported",
        )
    if not content:
        raise DocumentParseError("The file is empty (0 bytes).")
    if ext == "pdf" and not content[:1024].lstrip().startswith(b"%PDF"):
        raise DocumentParseError("File has a .pdf extension but is not a valid PDF (corrupted or renamed).")
    if ext == "docx" and not content.startswith(b"PK"):
        raise DocumentParseError("File has a .docx extension but is not a valid DOCX (corrupted or renamed).")
    return ext


def _extract_pdf(content: bytes) -> str:
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # fitz raises various internal errors
        raise DocumentParseError(f"Corrupted or unreadable PDF: {exc}") from exc
    if doc.needs_pass:
        raise DocumentParseError("The PDF is password-protected.")
    if doc.page_count == 0:
        raise DocumentParseError("The PDF has no pages.")

    pages, image_count = [], 0
    try:
        for page in doc:
            # "blocks" keeps reading order reasonable for multi-column layouts
            blocks = page.get_text("blocks", sort=True)
            pages.append("\n".join(b[4].strip() for b in blocks if b[4].strip()))
            image_count += len(page.get_images(full=False))
    except Exception as exc:
        raise DocumentParseError(f"Corrupted PDF content: {exc}") from exc
    finally:
        doc.close()

    text = "\n".join(pages).strip()
    if len(text) < MIN_TEXT_CHARS:
        if image_count:
            raise DocumentParseError(
                "This appears to be a scanned/image-only PDF. No selectable text was found; "
                "OCR is not enabled. Please upload a text-based PDF or DOCX."
            )
        raise DocumentParseError("The PDF contains no extractable text (empty document).")
    return text


def _extract_docx(content: bytes) -> str:
    try:
        document = docx.Document(io.BytesIO(content))
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise DocumentParseError(f"Corrupted or unreadable DOCX: {exc}") from exc
    except Exception as exc:
        raise DocumentParseError(f"Unable to open DOCX: {exc}") from exc

    lines = [p.text for p in document.paragraphs]
    # Tables are common in resumes (skills grids, two-column layouts)
    for table in document.tables:
        for row in table.rows:
            cells, seen = [], set()
            for cell in row.cells:  # merged cells repeat; de-duplicate
                t = cell.text.strip()
                if t and t not in seen:
                    seen.add(t)
                    cells.append(t)
            if cells:
                lines.append(" | ".join(cells))
    text = "\n".join(lines).strip()
    if len(text) < MIN_TEXT_CHARS:
        raise DocumentParseError("The DOCX contains no meaningful text (empty document).")
    return text


def extract_text(filename: str, content: bytes) -> tuple[str, str]:
    """Return (file_type, text)."""
    ftype = detect_file_type(filename, content)
    text = _extract_pdf(content) if ftype == "pdf" else _extract_docx(content)
    return ftype, text
