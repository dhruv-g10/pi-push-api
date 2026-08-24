import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter
import psutil

from server.app.config import settings

router = APIRouter(prefix="", tags=["System"])

SERVER_START_TIME = time.time()


def get_local_ip_addresses() -> List[str]:
    """Retrieve non-loopback IPv4 addresses."""
    ips = []
    try:
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    ips.append(f"{interface}: {addr.address}")
    except Exception:
        try:
            # Fallback
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ips


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    uptime_seconds = round(time.time() - SERVER_START_TIME, 2)
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "base_dir": str(settings.base_dir),
        "exec_enabled": settings.enable_exec,
    }


@router.get("/system")
async def system_diagnostics() -> Dict[str, Any]:
    """Retrieve detailed system statistics from the Raspberry Pi / host machine."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True)
    
    # Memory
    mem = psutil.virtual_memory()
    memory_info = {
        "total_mb": round(mem.total / (1024 * 1024), 2),
        "available_mb": round(mem.available / (1024 * 1024), 2),
        "used_mb": round(mem.used / (1024 * 1024), 2),
        "percent": mem.percent,
    }

    # Disk
    base_disk = psutil.disk_usage(str(settings.base_dir))
    disk_info = {
        "base_dir_path": str(settings.base_dir),
        "total_gb": round(base_disk.total / (1024 * 1024 * 1024), 2),
        "free_gb": round(base_disk.free / (1024 * 1024 * 1024), 2),
        "used_gb": round(base_disk.used / (1024 * 1024 * 1024), 2),
        "percent": base_disk.percent,
    }

    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "ip_addresses": get_local_ip_addresses(),
        "cpu": {
            "usage_percent": cpu_percent,
            "core_count": cpu_count,
        },
        "memory": memory_info,
        "disk": disk_info,
        "config": {
            "base_dir": str(settings.base_dir),
            "allow_absolute_paths": settings.allow_absolute_paths,
            "enable_exec": settings.enable_exec,
            "default_exec_timeout": settings.default_exec_timeout,
        }
    }
