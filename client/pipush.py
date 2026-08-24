#!/usr/bin/env python3
"""
PiPush CLI & Python SDK
Push files, synchronize directories, and run remote commands on your Raspberry Pi.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests


class PiPushClient:
    """Python SDK client for interacting with the Pi Push API server."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def health(self) -> Dict[str, Any]:
        """Check API server health."""
        resp = requests.get(f"{self.base_url}/health", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def system_status(self) -> Dict[str, Any]:
        """Fetch detailed system diagnostic stats from the Raspberry Pi."""
        resp = requests.get(f"{self.base_url}/system", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def upload_file(
        self,
        local_file_path: Path,
        target_dir: str = "",
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """Upload a single file to the Raspberry Pi."""
        local_file_path = Path(local_file_path)
        if not local_file_path.is_file():
            raise FileNotFoundError(f"Local file does not exist: {local_file_path}")

        with open(local_file_path, "rb") as f:
            files = [("files", (local_file_path.name, f))]
            data = {
                "target_dir": target_dir,
                "overwrite": str(overwrite).lower()
            }
            resp = requests.post(f"{self.base_url}/upload", files=files, data=data, timeout=60)
            resp.raise_for_status()
            return resp.json()

    def upload_directory(
        self,
        local_dir_path: Path,
        target_dir: str = "",
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """Upload an entire directory recursively, preserving relative structure."""
        local_dir_path = Path(local_dir_path).resolve()
        if not local_dir_path.is_dir():
            raise NotADirectoryError(f"Local directory does not exist: {local_dir_path}")

        all_files = [p for p in local_dir_path.rglob("*") if p.is_file()]
        if not all_files:
            return {"success": True, "count": 0, "message": "Directory is empty"}

        relative_map = {}
        files_payload = []
        open_handles = []

        try:
            for file_path in all_files:
                rel_str = str(file_path.relative_to(local_dir_path)).replace("\\", "/")
                # use file_path.name as form key, mapped via relative_paths_json
                safe_key = rel_str.replace("/", "_")
                relative_map[safe_key] = rel_str
                handle = open(file_path, "rb")
                open_handles.append(handle)
                files_payload.append(("files", (safe_key, handle)))

            data = {
                "target_dir": target_dir,
                "relative_paths_json": json.dumps(relative_map),
                "overwrite": str(overwrite).lower()
            }
            resp = requests.post(f"{self.base_url}/upload", files=files_payload, data=data, timeout=120)
            resp.raise_for_status()
            return resp.json()
        finally:
            for handle in open_handles:
                handle.close()

    def write_content(
        self,
        remote_path: str,
        content: str,
        is_base64: bool = False,
        overwrite: bool = True,
        make_executable: bool = False
    ) -> Dict[str, Any]:
        """Directly write text or base64 data to a file on the Raspberry Pi."""
        payload = {
            "path": remote_path,
            "content": content,
            "is_base64": is_base64,
            "overwrite": overwrite,
            "make_executable": make_executable
        }
        resp = requests.post(f"{self.base_url}/write", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute a shell command on the Raspberry Pi."""
        payload = {
            "command": command,
            "cwd": cwd,
            "timeout": timeout,
            "env": env
        }
        resp = requests.post(f"{self.base_url}/exec", json=payload, timeout=(timeout + 10 if timeout else 90))
        resp.raise_for_status()
        return resp.json()

    def browse(self, remote_path: str = "") -> Dict[str, Any]:
        """Browse remote directory or inspect file metadata."""
        resp = requests.get(f"{self.base_url}/browse", params={"path": remote_path}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def download(self, remote_path: str, local_save_path: Optional[Path] = None) -> bytes:
        """Download file content from the Raspberry Pi."""
        resp = requests.get(f"{self.base_url}/download", params={"path": remote_path}, timeout=60)
        resp.raise_for_status()
        if local_save_path:
            local_save_path = Path(local_save_path)
            local_save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_save_path, "wb") as f:
                f.write(resp.content)
        return resp.content

    def delete(self, remote_path: str, recursive: bool = False) -> Dict[str, Any]:
        """Delete a remote file or folder."""
        resp = requests.delete(
            f"{self.base_url}/delete",
            params={"path": remote_path, "recursive": str(recursive).lower()},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()


def format_size(size_bytes: Optional[int]) -> str:
    """Format bytes into human-readable string."""
    if size_bytes is None:
        return "-"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:3.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def cli_upload(client: PiPushClient, args):
    local_path = Path(args.local_path)
    if not local_path.exists():
        print(f"Error: Local path does not exist: {local_path}", file=sys.stderr)
        sys.exit(1)

    target_dir = args.remote_dir or ""
    overwrite = not args.no_overwrite
    display_target = target_dir if target_dir else "[base_dir]"

    if local_path.is_dir():
        print(f"Uploading directory '{local_path}' -> remote '{display_target}'...")
        result = client.upload_directory(local_path, target_dir=target_dir, overwrite=overwrite)
    else:
        print(f"Uploading file '{local_path.name}' -> remote '{display_target}'...")
        result = client.upload_file(local_path, target_dir=target_dir, overwrite=overwrite)

    if result.get("success"):
        count = result.get("count", len(result.get("files", [])))
        print(f"Successfully uploaded {count} file(s) to {result.get('target_dir')}")
        for f in result.get("files", []):
            print(f"  - {f.get('filename')} ({format_size(f.get('size_bytes'))}) -> {f.get('saved_path')}")
    else:
        print("Upload completed with status:", result)


def cli_write(client: PiPushClient, args):
    if args.stdin:
        content = sys.stdin.read()
    elif args.content is not None:
        content = args.content
    else:
        print("Error: Provide --content or --stdin", file=sys.stderr)
        sys.exit(1)

    print(f"Writing to '{args.remote_path}'...")
    res = client.write_content(
        remote_path=args.remote_path,
        content=content,
        overwrite=not args.no_overwrite,
        make_executable=args.executable
    )
    if res.get("success"):
        print(f"Successfully wrote {format_size(res.get('size_bytes'))} to {res.get('saved_path')}")
        if res.get("is_executable"):
            print("  - Marked as executable (+x)")
    else:
        print("Write failed:", res, file=sys.stderr)


def cli_exec(client: PiPushClient, args):
    command = " ".join(args.command)
    res = client.execute(command=command, cwd=args.cwd, timeout=args.timeout)

    if res.get("stdout"):
        sys.stdout.write(res["stdout"])
        if not res["stdout"].endswith("\n"):
            sys.stdout.write("\n")
    if res.get("stderr"):
        sys.stderr.write(res["stderr"])
        if not res["stderr"].endswith("\n"):
            sys.stderr.write("\n")

    if res.get("timed_out"):
        print(f"[Error: Command timed out after {args.timeout}s]", file=sys.stderr)

    sys.exit(res.get("exit_code", 0))


def cli_ls(client: PiPushClient, args):
    res = client.browse(args.remote_path or "")
    if res.get("is_dir"):
        print(f"\nDirectory: {res.get('path')} ({res.get('item_count')} items)\n")
        print(f"{'TYPE':<6} {'SIZE':<10} {'NAME':<35} {'PERMISSIONS':<12}")
        print("-" * 65)
        for item in res.get("items", []):
            item_type = "[DIR]" if item["is_dir"] else "[FILE]"
            size_str = format_size(item["size_bytes"])
            print(f"{item_type:<6} {size_str:<10} {item['name']:<35} {item.get('permissions', ''):<12}")
        print("")
    else:
        f = res.get("file", {})
        print(f"\nFile: {f.get('name')}")
        print(f"Path: {f.get('path')}")
        print(f"Size: {format_size(f.get('size_bytes'))}")
        print(f"Modified: {f.get('modified_at')}")
        print(f"SHA-256: {f.get('sha256')}\n")


def cli_cat(client: PiPushClient, args):
    content = client.download(args.remote_path)
    sys.stdout.buffer.write(content)


def cli_download(client: PiPushClient, args):
    dest = Path(args.local_path) if args.local_path else Path(Path(args.remote_path).name)
    print(f"Downloading '{args.remote_path}' -> '{dest}'...")
    client.download(args.remote_path, local_save_path=dest)
    print(f"Saved to {dest.resolve()} ({format_size(dest.stat().st_size)})")


def cli_rm(client: PiPushClient, args):
    res = client.delete(args.remote_path, recursive=args.recursive)
    if res.get("success"):
        print(f"Deleted: {res.get('deleted_path')}")


def cli_status(client: PiPushClient, args):
    sys_info = client.system_status()
    print("\n================ Raspberry Pi System Status ================")
    print(f" Hostname:        {sys_info.get('hostname')}")
    print(f" OS / Arch:       {sys_info.get('os')} ({sys_info.get('architecture')})")
    print(f" Python Version:  {sys_info.get('python_version')}")
    print(f" Uptime:          {sys_info.get('uptime_seconds')} seconds")
    print(f" IP Addresses:    {', '.join(sys_info.get('ip_addresses', []))}")
    print("------------------------------------------------------------")
    
    cpu = sys_info.get("cpu", {})
    print(f" CPU Usage:       {cpu.get('usage_percent')}% ({cpu.get('core_count')} cores)")

    mem = sys_info.get("memory", {})
    print(f" Memory:          {mem.get('used_mb')} MB / {mem.get('total_mb')} MB ({mem.get('percent')}%)")

    disk = sys_info.get("disk", {})
    print(f" Disk:            {disk.get('used_gb')} GB / {disk.get('total_gb')} GB ({disk.get('percent')}%)")
    print(f" Base Directory:  {disk.get('base_dir_path')}")
    print("============================================================\n")


def main():
    default_url = os.getenv("PI_PUSH_URL", "http://localhost:8000")

    parser = argparse.ArgumentParser(
        prog="pipush",
        description="PiPush: Remotely push files and execute commands on your Raspberry Pi."
    )
    parser.add_argument(
        "--url",
        default=default_url,
        help=f"Base URL of PiPush API (default: {default_url} or PI_PUSH_URL env var)"
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # upload
    p_upload = subparsers.add_parser("upload", help="Upload a file or directory to the Pi")
    p_upload.add_argument("local_path", help="Local file or directory path to upload")
    p_upload.add_argument("remote_dir", nargs="?", default="", help="Destination directory on the Pi")
    p_upload.add_argument("--no-overwrite", action="store_true", help="Do not overwrite existing files")

    # write
    p_write = subparsers.add_parser("write", help="Write direct string content to a file")
    p_write.add_argument("remote_path", help="Target remote file path")
    p_write.add_argument("--content", help="Text content to write")
    p_write.add_argument("--stdin", action="store_true", help="Read content from stdin")
    p_write.add_argument("--executable", "-x", action="store_true", help="Make file executable (chmod +x)")
    p_write.add_argument("--no-overwrite", action="store_true", help="Do not overwrite existing file")

    # exec / run
    p_exec = subparsers.add_parser("exec", aliases=["run"], help="Execute shell command on the Pi")
    p_exec.add_argument("command", nargs="+", help="Shell command string to run")
    p_exec.add_argument("--cwd", help="Remote working directory")
    p_exec.add_argument("--timeout", type=int, help="Command timeout in seconds")

    # ls
    p_ls = subparsers.add_parser("ls", help="List remote directory contents or inspect file")
    p_ls.add_argument("remote_path", nargs="?", default="", help="Remote directory or file path")

    # cat
    p_cat = subparsers.add_parser("cat", help="Print remote file contents to stdout")
    p_cat.add_argument("remote_path", help="Remote file path")

    # download
    p_dl = subparsers.add_parser("download", help="Download a file from the Pi")
    p_dl.add_argument("remote_path", help="Remote file path")
    p_dl.add_argument("local_path", nargs="?", default="", help="Local path to save downloaded file")

    # rm
    p_rm = subparsers.add_parser("rm", help="Delete remote file or directory")
    p_rm.add_argument("remote_path", help="Remote path to delete")
    p_rm.add_argument("-r", "--recursive", action="store_true", help="Delete directory recursively")

    # status
    subparsers.add_parser("status", help="Get Raspberry Pi system status (CPU, RAM, Disk, Uptime)")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    client = PiPushClient(base_url=args.url)

    try:
        if args.subcommand == "upload":
            cli_upload(client, args)
        elif args.subcommand == "write":
            cli_write(client, args)
        elif args.subcommand in ("exec", "run"):
            cli_exec(client, args)
        elif args.subcommand == "ls":
            cli_ls(client, args)
        elif args.subcommand == "cat":
            cli_cat(client, args)
        elif args.subcommand == "download":
            cli_download(client, args)
        elif args.subcommand == "rm":
            cli_rm(client, args)
        elif args.subcommand == "status":
            cli_status(client, args)
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to PiPush server at '{args.url}'. Make sure the server is running on the Raspberry Pi.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as err:
        try:
            err_json = err.response.json()
            detail = err_json.get("detail", str(err))
            print(f"API Error ({err.response.status_code}): {detail}", file=sys.stderr)
        except Exception:
            print(f"API Error ({err.response.status_code}): {err.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
