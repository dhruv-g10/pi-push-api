import hashlib
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

from server.app.config import settings


def resolve_safe_path(target_path: Optional[str] = None) -> Path:
    """
    Resolve a user-provided target path safely.
    - If empty, defaults to settings.base_dir.
    - If absolute and settings.allow_absolute_paths is True, resolves directly.
    - Otherwise, resolves relative to settings.base_dir with path traversal protection.
    """
    if not target_path or target_path.strip() in ("", ".", "/"):
        return settings.base_dir

    raw_path = Path(target_path.strip())

    if raw_path.is_absolute():
        if settings.allow_absolute_paths:
            return raw_path.resolve()
        else:
            # Strip drive / leading root to force sandboxing
            relative_parts = [p for p in raw_path.parts if p not in (raw_path.drive, raw_path.root, "/", "\\")]
            candidate = (settings.base_dir / Path(*relative_parts)).resolve()
    else:
        candidate = (settings.base_dir / raw_path).resolve()

    if not settings.allow_absolute_paths:
        # Enforce sandbox
        try:
            candidate.relative_to(settings.base_dir)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Access denied: Target path is outside base directory {settings.base_dir}"
            )

    return candidate


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_file_metadata(path: Path) -> Dict[str, Any]:
    """Retrieve detailed metadata for a file or directory."""
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    stat_info = path.stat()
    is_dir = path.is_dir()
    
    # Calculate formatted modified date
    mtime = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).isoformat()
    
    info: Dict[str, Any] = {
        "name": path.name if path.name else str(path),
        "path": str(path.resolve()),
        "is_dir": is_dir,
        "is_symlink": path.is_symlink(),
        "size_bytes": stat_info.st_size if not is_dir else None,
        "permissions": oct(stat.S_IMODE(stat_info.st_mode)),
        "modified_at": mtime,
    }

    if not is_dir and stat_info.st_size < 100 * 1024 * 1024:  # Only hash files < 100MB
        try:
            info["sha256"] = calculate_sha256(path)
        except Exception:
            info["sha256"] = None

    return info


def list_directory_contents(dir_path: Path) -> List[Dict[str, Any]]:
    """List contents of a directory with metadata for each item."""
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {dir_path}")

    items = []
    try:
        for entry in dir_path.iterdir():
            try:
                stat_info = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "is_dir": entry.is_dir(),
                    "size_bytes": stat_info.st_size if not entry.is_dir() else None,
                    "modified_at": datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).isoformat(),
                    "permissions": oct(stat.S_IMODE(stat_info.st_mode)),
                })
            except (PermissionError, FileNotFoundError):
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied reading directory: {dir_path}")

    # Sort directories first, then alphabetical
    return sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))
