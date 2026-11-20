from fastapi.testclient import TestClient

from app import main


class _Resp:
    def __init__(self, url):
        self.url = url

    def json(self):
        if self.url.endswith("/task"):
            return {"Family": "ilmp-calc-engine-dev", "Revision": "7"}
        return {"Image": "repo/calc-engine@sha256:abc", "ImageID": "sha256:other"}


def test_version_reports_running_task_definition(monkeypatch):
    monkeypatch.setenv("ECS_CONTAINER_METADATA_URI_V4", "http://169.254.170.2/v4/x")
    monkeypatch.setattr(main.httpx, "get", lambda url, **k: _Resp(url))
    main._running_image.cache_clear()
    body = TestClient(main.app).get("/version").json()
    assert body["image_digest"] == "sha256:abc"
    assert body["task_definition"] == "ilmp-calc-engine-dev:7"
    main._running_image.cache_clear()
