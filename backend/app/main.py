"""Avenry local research API and compiled web application."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config import DATA, ROOT
from backend.app.db import Analysis, ModelVersion, Result, Scene, Session
from backend.app.services.catalog import model_info, public_scene, sync_catalog
from backend.app.services.inference import run_analysis

logging.basicConfig(level=logging.INFO)
submission_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    DATA.mkdir(parents=True, exist_ok=True)
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    sync_catalog()
    with Session.begin() as db:
        db.execute(
            update(Analysis)
            .where(Analysis.status.in_(["queued", "running"]))
            .values(
                status="failed",
                error="Server restarted before completion. Submit a new analysis.",
            )
        )
    app.state.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="terrasense")
    yield
    app.state.worker.shutdown(wait=True)


app = FastAPI(
    title="Avenry Earth Intelligence",
    version="0.2.0",
    lifespan=lifespan,
    description="Local satellite surface-water research prototype. Predictions do not verify flooding.",
)


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": str(exc.status_code), "message": exc.detail}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid request",
                "fields": [{"location": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
            }
        },
    )


class HealthResponse(BaseModel):
    status: str


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(status="ok")


@app.get("/api/v1/system", tags=["system"])
def system():
    info = model_info()
    return {
        "model_ready": info is not None,
        "model": info,
        "interpretation": "surface_water_only",
        "job_backend": "single local worker",
        "hls_inference_enabled": False,
    }


@app.get("/api/v1/scenes", tags=["scenes"])
def scenes(
    bbox: str | None = Query(default=None, description="west,south,east,north in WGS84"),
):
    with Session() as db:
        rows = sorted(
            db.scalars(select(Scene)),
            key=lambda r: (
                {"test": 0, "validation": 1, "train": 2, "demo": 3}.get(r.details.get("split"), 4),
                r.id,
            ),
        )
        if bbox:
            try:
                west, south, east, north = map(float, bbox.split(","))
                if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                    raise ValueError()
            except ValueError:
                raise HTTPException(
                    422,
                    "bbox must be west,south,east,north with valid increasing coordinates",
                )
            rows = [
                r
                for r in rows
                if r.details["bounds"][0] <= east
                and r.details["bounds"][2] >= west
                and r.details["bounds"][1] <= north
                and r.details["bounds"][3] >= south
            ]
        return {"items": [public_scene(r) for r in rows], "total": len(rows)}


@app.get("/api/v1/scenes/{scene_id}", tags=["scenes"])
def scene_detail(scene_id: str):
    with Session() as db:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise HTTPException(404, "Scene not found")
        return public_scene(scene)


@app.get("/api/v1/scenes/{scene_id}/assets/{layer}", tags=["scenes"])
def scene_asset(scene_id: str, layer: Literal["radar", "optical", "label"]):
    scene_detail(scene_id)
    path = (DATA / "processed" / scene_id / f"{layer}.png").resolve()
    if not path.is_relative_to(DATA / "processed") or not path.is_file():
        raise HTTPException(404, "Preview not available")
    return FileResponse(path, media_type="image/png")


def public_job(job):
    return {
        "id": job.id,
        "scene_id": job.scene_id,
        "model_version": job.model_id,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "error": job.error,
    }


@app.post("/api/v1/analyses", status_code=202, tags=["analyses"])
def create_analysis(body: AnalysisRequest, request: Request):
    with submission_lock, Session.begin() as db:
        if not db.get(Scene, body.scene_id):
            raise HTTPException(404, "Scene not found")
        info = model_info()
        if info is None:
            raise HTTPException(
                409,
                "No verified trained checkpoint. Run the documented training command first.",
            )
        if not db.get(ModelVersion, info["version"]):
            db.add(ModelVersion(id=info["version"], details=info))
        pending = list(db.scalars(select(Analysis).where(Analysis.status.in_(["queued", "running"]))))
        if len(pending) >= 4:
            raise HTTPException(429, "Local analysis queue is full; wait for an existing job")
        job = Analysis(
            id=str(uuid4()),
            scene_id=body.scene_id,
            model_id=info["version"],
            status="queued",
        )
        db.add(job)
        db.flush()
        result = public_job(job)
    # Submitting after commit prevents the worker from racing an uncommitted job.
    request.app.state.worker.submit(run_analysis, result["id"])
    return result


@app.get("/api/v1/analyses", tags=["analyses"])
def analyses(limit: int = Query(default=20, ge=1, le=100)):
    with Session() as db:
        return {
            "items": [
                public_job(j)
                for j in db.scalars(select(Analysis).order_by(Analysis.created_at.desc()).limit(limit))
            ]
        }


@app.get("/api/v1/analyses/{analysis_id}", tags=["analyses"])
def analysis_detail(analysis_id: UUID):
    with Session() as db:
        job = db.get(Analysis, str(analysis_id))
        if not job:
            raise HTTPException(404, "Analysis not found")
        return public_job(job)


@app.get("/api/v1/analyses/{analysis_id}/results", tags=["analyses"])
def analysis_results(analysis_id: UUID):
    job = analysis_detail(analysis_id)
    if job["status"] != "completed":
        raise HTTPException(409, f"Results unavailable while analysis is {job['status']}")
    with Session() as db:
        return db.get(Result, str(analysis_id)).details


@app.get("/api/v1/analyses/{analysis_id}/files/{filename}", tags=["analyses"])
def result_file(
    analysis_id: UUID,
    filename: Literal["water-mask.tif", "prediction.png", "result.json"],
):
    analysis_results(analysis_id)
    path = DATA / "results" / str(analysis_id) / filename
    if not path.is_file():
        raise HTTPException(404, "Result file is missing")
    return FileResponse(
        path,
        media_type={
            "water-mask.tif": "image/tiff",
            "prediction.png": "image/png",
            "result.json": "application/json",
        }[filename],
        filename=filename if filename != "prediction.png" else None,
    )


# The compiled frontend is served by the same origin as the API.
if (ROOT / "frontend/dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "frontend/dist", html=True), name="web")
