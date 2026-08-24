import base64
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from server.app.utils import (
    calculate_sha256,
    get_file_metadata,
    list_directory_contents,
    resolve_safe_path,
)

router = APIRouter(prefix="", tags=["Files"])


class WriteRequest(BaseModel):
    """Payload for direct content write."""
    path: str = Field(..., description="Target file path (absolute or relative to base_dir)")
    content: str = Field(..., description="File content (plain text or base64 encoded string)")
    is_base64: bool = Field(default=False, description="Set to true if content is base64 encoded")
    overwrite: bool = Field(default=True, description="Whether to overwrite if file exists")
    make_executable: bool = Field(default=False, description="Set executable chmod (+x) on Unix systems")


@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(..., description="One or more files to upload"),
    target_dir: Optional[str] = Form(default="", description="Destination directory path"),
    relative_paths_json: Optional[str] = Form(
        default=None,
        description='Optional JSON mapping of filename to relative path for preserving folder structure, e.g. {"app.py": "src/app.py"}'
    ),
    overwrite: bool = Form(default=True, description="Whether to overwrite existing files"),
) -> Dict[str, Any]:
    """
    Upload one or more files to the Raspberry Pi.
    Preserves folder hierarchy if relative path mapping is provided.
    """
    dest_dir = resolve_safe_path(target_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    relative_map: Dict[str, str] = {}
    if relative_paths_json:
        try:
            relative_map = json.loads(relative_paths_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid relative_paths_json: {e}")

    uploaded_files = []

    for upload_file in files:
        filename = upload_file.filename or "uploaded_file"
        rel_path = relative_map.get(filename, filename)
        target_file_path = (dest_dir / rel_path).resolve()

        # Path sandboxing check
        if not target_file_path.is_relative_to(dest_dir) and not resolve_safe_path(str(target_file_path)):
            raise HTTPException(status_code=400, detail=f"Invalid file path traversal: {rel_path}")

        # Check existing file
        if target_file_path.exists() and not overwrite:
            raise HTTPException(status_code=409, detail=f"File already exists and overwrite=false: {target_file_path}")

        # Ensure parent directories exist
        target_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Stream save
        with open(target_file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)

        file_stat = target_file_path.stat()
        uploaded_files.append({
            "filename": filename,
            "saved_path": str(target_file_path),
            "size_bytes": file_stat.st_size,
            "sha256": calculate_sha256(target_file_path),
        })

    return {
        "success": True,
        "count": len(uploaded_files),
        "target_dir": str(dest_dir),
        "files": uploaded_files,
    }


@router.post("/write")
async def write_file_content(payload: WriteRequest) -> Dict[str, Any]:
    """
    Directly write raw string or base64 data to a file on the Raspberry Pi.
    Useful for pushing code snippets, configuration files, and scripts without multipart encoding.
    """
    target_path = resolve_safe_path(payload.path)

    if target_path.exists() and not payload.overwrite:
        raise HTTPException(status_code=409, detail=f"File already exists: {target_path}")

    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if payload.is_base64:
        try:
            data = base64.b64decode(payload.content)
            with open(target_path, "wb") as f:
                f.write(data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to decode base64 content: {e}")
    else:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(payload.content)

    if payload.make_executable:
        try:
            current_mode = target_path.stat().st_mode
            target_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass  # Silently ignore on non-POSIX systems if unsupported

    stat_info = target_path.stat()
    return {
        "success": True,
        "saved_path": str(target_path),
        "size_bytes": stat_info.st_size,
        "sha256": calculate_sha256(target_path),
        "is_executable": os.access(target_path, os.X_OK),
    }


@router.get("/browse")
async def browse_path(
    path: Optional[str] = Query(default="", description="Path to browse or inspect")
) -> Dict[str, Any]:
    """
    Browse a directory or inspect metadata of a file on the Raspberry Pi.
    """
    target_path = resolve_safe_path(path)

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Path does not exist: {target_path}")

    if target_path.is_dir():
        items = list_directory_contents(target_path)
        return {
            "is_dir": True,
            "path": str(target_path),
            "item_count": len(items),
            "items": items,
        }
    else:
        metadata = get_file_metadata(target_path)
        return {
            "is_dir": False,
            "file": metadata,
        }


@router.get("/download")
async def download_file(
    path: str = Query(..., description="Path of file to download")
) -> FileResponse:
    """
    Download a file from the Raspberry Pi.
    """
    target_path = resolve_safe_path(path)

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {target_path}")

    if target_path.is_dir():
        raise HTTPException(status_code=400, detail="Cannot download a directory directly. Specify a file path.")

    return FileResponse(
        path=str(target_path),
        filename=target_path.name,
        media_type="application/octet-stream"
    )


@router.delete("/delete")
async def delete_path(
    path: str = Query(..., description="Path of file or directory to delete"),
    recursive: bool = Query(default=False, description="Allow deleting non-empty directories recursively")
) -> Dict[str, Any]:
    """
    Delete a file or directory on the Raspberry Pi.
    """
    target_path = resolve_safe_path(path)

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {target_path}")

    if target_path.is_dir():
        if recursive:
            shutil.rmtree(target_path)
        else:
            try:
                target_path.rmdir()
            except OSError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Directory is not empty. Use recursive=true to delete: {target_path}"
                )
    else:
        target_path.unlink()

    return {
        "success": True,
        "deleted_path": str(target_path),
    }
