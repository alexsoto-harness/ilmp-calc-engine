"""ILMP calc engine: runs index backtests for Index Studio.

Endpoints:
  GET  /health            liveness for the ALB target group
  GET  /version           build identity; FR-008 asserts image_digest after every deploy
  POST /backtest          queue a backtest job, returns job_id
  GET  /backtest/{job_id} job status: QUEUED -> RUNNING -> COMPLETED | FAILED
"""

import os
from functools import lru_cache

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import backtest, jobs

app = FastAPI(title="ILMP calc engine", version="1.0.0")


class BacktestRequest(BaseModel):
    index_id: str = Field(default="SPDJI-DEMO-50", min_length=1, max_length=64)
    days: int = Field(default=3, ge=1, le=30)


@lru_cache(maxsize=1)
def _running_image() -> tuple[str, str, str]:
    """Return (image, digest, task_definition) of the running container.

    On ECS the task metadata endpoint reports the digest that was actually
    pulled and the task definition revision, so /version proves what is
    running rather than what CI intended.
    """
    uri = os.getenv("ECS_CONTAINER_METADATA_URI_V4")
    if uri:
        try:
            meta = httpx.get(uri, timeout=2.0).json()
            task = httpx.get(f"{uri}/task", timeout=2.0).json()
            image = meta.get("Image", "")
            digest = meta.get("ImageID", "")
            if "@sha256:" in image:
                digest = image.split("@", 1)[1]
            taskdef = f"{task.get('Family', '')}:{task.get('Revision', '')}"
            return image, digest or "unknown", taskdef
        except (httpx.HTTPError, ValueError):
            pass
    return os.getenv("IMAGE_REF", "local"), os.getenv("IMAGE_DIGEST", "unknown"), "local"


@app.get("/health")
def health() -> dict:
    return {"status": "UP", "component": "calc-engine"}


@app.get("/version")
def version() -> dict:
    image, digest, taskdef = _running_image()
    return {
        "component": "calc-engine",
        "image": image,
        "image_digest": digest,
        "task_definition": taskdef,
        "image_tag": os.getenv("IMAGE_TAG", "dev"),
        "commit_sha": os.getenv("GIT_SHA", "unknown"),
        "build_number": os.getenv("BUILD_NUMBER", "0"),
        "environment": os.getenv("ENVIRONMENT", "local"),
    }


@app.post("/backtest", status_code=202)
def create_backtest(req: BacktestRequest) -> dict:
    job_id = jobs.submit(req.index_id, req.days)
    return {"job_id": job_id, "status": jobs.QUEUED}


@app.get("/backtest/{job_id}")
def get_backtest(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.get("/backtest/{job_id}/analytics")
def get_backtest_analytics(job_id: str) -> dict:
    """FR-102: period return of a completed backtest versus the base level."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job["status"] != jobs.COMPLETED:
        raise HTTPException(status_code=409, detail=f"job is {job['status']}")
    period_return = job["index_level"] / backtest.BASE_LEVEL - 1
    return {
        "job_id": job_id,
        "index_id": job["index_id"],
        "days": job["days"],
        "period_return_pct": round(period_return * 100, 4),
    }
