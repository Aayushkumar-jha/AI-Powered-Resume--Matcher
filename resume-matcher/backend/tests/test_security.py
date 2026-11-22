from pathlib import Path

import pytest

from app.api.routes.analysis import _csv_safe
from app.core.security import resolve_stored, safe_filename, store_file


@pytest.mark.parametrize("raw,expected", [
    ("../../etc/passwd", "passwd"),
    ("C:\\Users\\x\\resume.pdf", "resume.pdf"),
    ("my résumé (final).docx", "my resume _final_.docx"),
    ("", "file"),
    ("<script>.pdf", "_script_.pdf"),
])
def test_safe_filename(raw, expected):
    assert safe_filename(raw) == expected


def test_safe_filename_truncates_but_keeps_extension():
    name = safe_filename("a" * 300 + ".pdf")
    assert len(name) <= 120 and name.endswith(".pdf")


def test_store_file_uses_random_names(tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path)
    rel = store_file(1, "pdf", b"%PDF-1.4")
    assert rel.startswith("job_1/") and len(Path(rel).stem) == 32
    assert resolve_stored(rel).read_bytes() == b"%PDF-1.4"
    with pytest.raises(ValueError):
        resolve_stored("../../outside.txt")


def test_csv_formula_injection_is_neutralized():
    assert _csv_safe("=HYPERLINK(\"evil\")").startswith("'=")
    assert _csv_safe("Alice") == "Alice"
    assert _csv_safe(None) == ""
