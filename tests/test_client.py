import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from client.pipush import PiPushClient
from server.app.config import settings
from server.app.main import app




def test_pipush_client_methods(monkeypatch):
    temp_dir = tempfile.mkdtemp(prefix="pipush_client_test_")
    monkeypatch.setattr(settings, "base_dir", Path(temp_dir).resolve())
    monkeypatch.setattr(settings, "allow_absolute_paths", True)
    monkeypatch.setattr(settings, "enable_exec", True)

    fastapi_test_client = TestClient(app)

    # Monkeypatch requests calls in pipush to route directly through FastAPI TestClient
    client = PiPushClient(base_url="http://testserver")

    def mock_get(url, params=None, timeout=None):
        endpoint = url.replace("http://testserver", "")
        return fastapi_test_client.get(endpoint, params=params)

    def mock_post(url, data=None, json=None, files=None, timeout=None):
        endpoint = url.replace("http://testserver", "")
        return fastapi_test_client.post(endpoint, data=data, json=json, files=files)

    def mock_delete(url, params=None, timeout=None):
        endpoint = url.replace("http://testserver", "")
        return fastapi_test_client.delete(endpoint, params=params)

    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.post", mock_post)
    monkeypatch.setattr("requests.delete", mock_delete)

    # 1. Health
    health = client.health()
    assert health["status"] == "healthy"

    # 2. Write content
    write_res = client.write_content("test_from_client.txt", "client content")
    assert write_res["success"] is True

    # 3. Browse
    browse_res = client.browse("")
    assert browse_res["is_dir"] is True
    assert any(item["name"] == "test_from_client.txt" for item in browse_res["items"])

    # 4. Download
    content = client.download("test_from_client.txt")
    assert content == b"client content"

    # 5. Execute command
    import sys
    exec_res = client.execute(f'"{sys.executable}" -c "print(\'cli exec ok\')"')
    assert exec_res["success"] is True
    assert "cli exec ok" in exec_res["stdout"]

    # 6. Delete
    del_res = client.delete("test_from_client.txt")
    assert del_res["success"] is True

    # Clean up
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
