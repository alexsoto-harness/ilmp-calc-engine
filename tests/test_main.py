import time

import pytest
from fastapi.testclient import TestClient

from app import backtest, main


@pytest.fixture(autouse=True)
def fast_jobs(monkeypatch, tmp_path):
    monkeypatch.setenv("BACKTEST_SECONDS", "0.2")
    monkeypatch.setattr("app.jobs._DB_PATH", str(tmp_path / "calc.db"))
    monkeypatch.delenv("ECS_CONTAINER_METADATA_URI_V4", raising=False)
    main._running_image.cache_clear()


@pytest.fixture
def client():
    return TestClient(main.app)


def wait_for(client, job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/backtest/{job_id}").json()
        if job["status"] in ("COMPLETED", "FAILED"):
            return job
        time.sleep(0.05)
    raise AssertionError("backtest did not finish")


def test_health(client):
    assert client.get("/health").json() == {"status": "UP", "component": "calc-engine"}


def test_version_reports_build_identity(client, monkeypatch):
    monkeypatch.setenv("IMAGE_TAG", "RC-calc-engine-42-abc1234")
    monkeypatch.setenv("GIT_SHA", "abc1234")
    monkeypatch.setenv("BUILD_NUMBER", "42")
    body = client.get("/version").json()
    assert body["image_tag"] == "RC-calc-engine-42-abc1234"
    assert body["commit_sha"] == "abc1234"
    assert body["build_number"] == "42"


def test_version_digest_falls_back_to_env(client, monkeypatch):
    monkeypatch.setenv("IMAGE_DIGEST", "sha256:feed")
    assert client.get("/version").json()["image_digest"] == "sha256:feed"


def test_version_digest_from_ecs_metadata(client, monkeypatch):
    class Resp:
        def json(self):
            return {"Image": "repo/calc-engine@sha256:abc", "ImageID": "sha256:other"}

    monkeypatch.setenv("ECS_CONTAINER_METADATA_URI_V4", "http://169.254.170.2/v4/x")
    monkeypatch.setattr(main.httpx, "get", lambda *a, **k: Resp())
    assert client.get("/version").json()["image_digest"] == "sha256:abc"


def test_backtest_queued_then_completed(client):
    resp = client.post("/backtest", json={"index_id": "SPDJI-DEMO-50", "days": 3})
    assert resp.status_code == 202
    assert resp.json()["status"] == "QUEUED"
    job = wait_for(client, resp.json()["job_id"])
    assert job["status"] == "COMPLETED"
    assert job["index_level"] > 0


def test_backtest_passes_through_running(client):
    job_id = client.post("/backtest", json={}).json()["job_id"]
    seen = set()
    deadline = time.time() + 5
    while time.time() < deadline:
        status = client.get(f"/backtest/{job_id}").json()["status"]
        seen.add(status)
        if status == "COMPLETED":
            break
        time.sleep(0.02)
    assert {"RUNNING", "COMPLETED"} <= seen


def test_backtest_unknown_job_404(client):
    assert client.get("/backtest/doesnotexist").status_code == 404


@pytest.mark.parametrize("days", [0, 31])
def test_backtest_rejects_out_of_range_days(client, days):
    assert client.post("/backtest", json={"days": days}).status_code == 422


def test_backtest_is_deterministic():
    assert backtest.run_backtest("SPDJI-DEMO-50", 3) == backtest.run_backtest("SPDJI-DEMO-50", 3)


def test_index_levels_start_at_base():
    levels = backtest.index_levels(backtest.constituent_prices("X", 3))
    assert levels[0] == backtest.BASE_LEVEL
    assert len(levels) == 4
