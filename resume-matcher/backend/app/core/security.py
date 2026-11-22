"""Security helpers: API-key protection, safe filenames, secure file storage."""
import hashlib
import re
import secrets
import unicodedata
import uuid
from pathlib import Path

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """If API_KEY is configured, every API request must present it (protects documents & PII)."""
    expected = get_settings().api_key
    if expected and not (x_api_key and secrets.compare_digest(x_api_key, expected)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")


def safe_filename(name: str, max_len: int = 120) -> str:
    """Strip paths and dangerous characters from a user-supplied filename (display only)."""
    name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    name = Path(name.replace("\\", "/")).name  # drop any directory components
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    name = re.sub(r"_{2,}", "_", name)
    if not name:
        name = "file"
    if len(name) > max_len:
        stem, dot, ext = name.rpartition(".")
        name = (stem[: max_len - len(ext) - 1] + "." + ext) if dot else name[:max_len]
    return name


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_file(job_id: int, ext: str, content: bytes) -> str:
    """Store bytes under a random UUID name (never the user's filename) outside any web root.
    Returns the stored relative path."""
    base = Path(get_settings().upload_dir).resolve()
    folder = base / f"job_{int(job_id)}"
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.{ext}"
    path = (folder / stored).resolve()
    if base not in path.parents:  # defence in depth against path traversal
        raise ValueError("Invalid storage path")
    path.write_bytes(content)
    path.chmod(0o600)
    return f"job_{int(job_id)}/{stored}"


def resolve_stored(relative: str) -> Path:
    base = Path(get_settings().upload_dir).resolve()
    path = (base / relative).resolve()
    if base not in path.parents:
        raise ValueError("Invalid storage path")
    return path
