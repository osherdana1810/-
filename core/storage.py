"""Save and delete uploaded files. Files get random names; originals are not kept on disk."""
from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
MAX_BYTES = 10 * 1024 * 1024


def _uploads_dir(data_dir: str | Path) -> Path:
    path = Path(data_dir) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(data_dir: str | Path, original_name: str, content: bytes) -> tuple[str, str]:
    """Store bytes under a random name. Returns (relative_path, sha256_hex)."""
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {ext or 'none'}")
    if len(content) > MAX_BYTES:
        raise ValueError("file is larger than 10 MB")
    digest = hashlib.sha256(content).hexdigest()
    name = f"{uuid.uuid4().hex}{ext}"
    target = _uploads_dir(data_dir) / name
    target.write_bytes(content)
    return str(Path("uploads") / name), digest


def absolute_path(data_dir: str | Path, relative: str) -> Path:
    return Path(data_dir) / relative


def delete_file(data_dir: str | Path, relative: str) -> None:
    path = absolute_path(data_dir, relative)
    if path.exists():
        path.unlink()


def delete_all_files(data_dir: str | Path) -> None:
    shutil.rmtree(_uploads_dir(data_dir), ignore_errors=True)


def media_type_for(relative: str) -> str:
    ext = Path(relative).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")
