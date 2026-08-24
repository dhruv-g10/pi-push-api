import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from server.app.config import settings
from server.app.main import app


@pytest.fixture(autouse=True)
def setup_temp_base_dir(monkeypatch):
    """Set up an isolated temporary base directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="pipush_test_")
    monkeypatch.setattr(settings, "base_dir", Path(temp_dir).resolve())
    monkeypatch.setattr(settings, "allow_absolute_paths", True)
    monkeypatch.setattr(settings, "enable_exec", True)
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert data["exec_enabled"] is True


def test_system_diagnostics(client):
    response = client.get("/system")
    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data


def test_upload_single_file(client, setup_temp_base_dir):
    content = b"Hello from automated tests!"
    files = {"files": ("test_file.txt", content, "text/plain")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 1
    
    saved_file = setup_temp_base_dir / "test_file.txt"
    assert saved_file.exists()
    assert saved_file.read_bytes() == content


def test_upload_nested_structure(client, setup_temp_base_dir):
    import json
    files = [
        ("files", ("main.py", b"print('hello')", "text/plain")),
        ("files", ("helper.py", b"def helper(): pass", "text/plain")),
    ]
    rel_map = {
        "main.py": "src/main.py",
        "helper.py": "src/utils/helper.py"
    }
    data = {"relative_paths_json": json.dumps(rel_map)}
    response = client.post("/upload", files=files, data=data)
    
    assert response.status_code == 200
    assert (setup_temp_base_dir / "src" / "main.py").exists()
    assert (setup_temp_base_dir / "src" / "utils" / "helper.py").exists()


def test_write_text_and_base64(client, setup_temp_base_dir):
    # Test plain text write
    resp = client.post("/write", json={
        "path": "config/app.json",
        "content": '{"debug": true}',
        "overwrite": True
    })
    assert resp.status_code == 200
    target = setup_temp_base_dir / "config" / "app.json"
    assert target.exists()
    assert target.read_text() == '{"debug": true}'

    # Test base64 write
    import base64
    b64_content = base64.b64encode(b"binary data \x00\x01\x02").decode("ascii")
    resp_b64 = client.post("/write", json={
        "path": "binary.dat",
        "content": b64_content,
        "is_base64": True
    })
    assert resp_b64.status_code == 200
    assert (setup_temp_base_dir / "binary.dat").read_bytes() == b"binary data \x00\x01\x02"


def test_browse_and_download(client, setup_temp_base_dir):
    # Create test files
    (setup_temp_base_dir / "dir1").mkdir()
    (setup_temp_base_dir / "dir1" / "file1.txt").write_text("file1 content")

    # Browse directory
    resp_browse = client.get("/browse", params={"path": ""})
    assert resp_browse.status_code == 200
    data = resp_browse.json()
    assert data["is_dir"] is True
    assert any(item["name"] == "dir1" for item in data["items"])

    # Download file
    resp_dl = client.get("/download", params={"path": "dir1/file1.txt"})
    assert resp_dl.status_code == 200
    assert resp_dl.content == b"file1 content"


def test_delete_file_and_folder(client, setup_temp_base_dir):
    test_file = setup_temp_base_dir / "delete_me.txt"
    test_file.write_text("temp")
    
    del_resp = client.delete("/delete", params={"path": "delete_me.txt"})
    assert del_resp.status_code == 200
    assert not test_file.exists()

    # Recursive directory delete
    test_dir = setup_temp_base_dir / "nested_dir"
    test_dir.mkdir()
    (test_dir / "inner.txt").write_text("inner")

    del_dir_resp = client.delete("/delete", params={"path": "nested_dir", "recursive": True})
    assert del_dir_resp.status_code == 200
    assert not test_dir.exists()


def test_exec_command(client, setup_temp_base_dir):
    import sys
    resp = client.post("/exec", json={
        "command": f'"{sys.executable}" -c "print(\'test execution output\')"',
        "timeout": 10
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["exit_code"] == 0
    assert "test execution output" in data["stdout"]


def test_exec_error_and_exit_code(client):
    import sys
    resp = client.post("/exec", json={
        "command": f'"{sys.executable}" -c "import sys; sys.stderr.write(\'err_msg\\n\'); sys.exit(42)"',
        "timeout": 10
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["exit_code"] == 42
    assert "err_msg" in data["stderr"]

