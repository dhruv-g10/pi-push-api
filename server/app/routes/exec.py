import asyncio
import os
import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.app.config import settings
from server.app.utils import resolve_safe_path

router = APIRouter(prefix="", tags=["Execution"])


class ExecRequest(BaseModel):
    """Payload to execute a shell command on the Raspberry Pi."""
    command: str = Field(..., description="Shell command string to execute")
    cwd: Optional[str] = Field(default=None, description="Working directory for the command")
    timeout: Optional[int] = Field(default=None, description="Execution timeout in seconds")
    env: Optional[Dict[str, str]] = Field(default=None, description="Additional environment variables")


class ExecResponse(BaseModel):
    """Result of command execution."""
    success: bool
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    command: str
    cwd: str


@router.post("/exec", response_model=ExecResponse)
async def execute_command(payload: ExecRequest) -> ExecResponse:
    """
    Execute a shell command on the Raspberry Pi.
    Captures stdout, stderr, exit code, and execution time.
    """
    if not settings.enable_exec:
        raise HTTPException(
            status_code=403,
            detail="Command execution is disabled in server configuration (PI_PUSH_ENABLE_EXEC=false)"
        )

    # Determine working directory
    working_dir = resolve_safe_path(payload.cwd) if payload.cwd else settings.base_dir
    if not working_dir.exists():
        raise HTTPException(status_code=400, detail=f"Working directory does not exist: {working_dir}")

    # Build environment
    cmd_env = os.environ.copy()
    if payload.env:
        cmd_env.update(payload.env)

    timeout = payload.timeout if payload.timeout is not None else settings.default_exec_timeout

    start_time = time.perf_counter()
    timed_out = False
    stdout_str = ""
    stderr_str = ""
    exit_code: Optional[int] = None

    try:
        process = await asyncio.create_subprocess_shell(
            payload.command,
            cwd=str(working_dir),
            env=cmd_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=float(timeout)
            )
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode
        except asyncio.TimeoutError:
            timed_out = True
            try:
                process.kill()
            except ProcessLookupError:
                pass
            stderr_str = f"Command timed out after {timeout} seconds"
            exit_code = -1

    except Exception as e:
        stderr_str = f"Failed to spawn process: {e}"
        exit_code = -1

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return ExecResponse(
        success=(exit_code == 0 and not timed_out),
        exit_code=exit_code,
        stdout=stdout_str,
        stderr=stderr_str,
        duration_ms=duration_ms,
        timed_out=timed_out,
        command=payload.command,
        cwd=str(working_dir),
    )
