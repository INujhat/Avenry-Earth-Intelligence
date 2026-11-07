"""One bounded local worker; results are persisted before marking success."""

import json
import logging
import time

import torch

from backend.app.config import ARTIFACTS, DATA
from backend.app.db import Analysis, Result, Scene, Session
from backend.app.services.catalog import local_path, model_info
from ml.geospatial import (
    area_km2,
    mask_preview,
    metrics,
    normalize,
    read_pair,
    write_mask,
)
from ml.model import UNet
from ml.train import predict

log = logging.getLogger(__name__)


def run_analysis(analysis_id):
    start = time.monotonic()
    try:
        with Session.begin() as db:
            job = db.get(Analysis, analysis_id)
            job.status = "running"
            row = db.get(Scene, job.scene_id).details
            expected_model = job.model_id
        info = model_info()
        if info is None or info["version"] != expected_model:
            raise ValueError("Selected model is no longer available")
        torch.set_num_threads(2)
        checkpoint = torch.load(ARTIFACTS / "model.pt", map_location="cpu", weights_only=True)
        model = UNet()
        model.load_state_dict(checkpoint["state_dict"])
        x, y, valid, profile = read_pair(local_path(row["radar"]), local_path(row["label"]))
        probability = predict(model, normalize(x))
        prediction = probability >= 0.5
        output = DATA / "results" / analysis_id
        output.mkdir(parents=True, exist_ok=True)
        write_mask(output / "water-mask.tif", prediction, valid, profile)
        mask_preview(output / "prediction.png", prediction, valid)
        result = {
            "analysis_id": analysis_id,
            "scene_id": row["id"],
            "interpretation": "detected_surface_water",
            "threshold": 0.5,
            "detected_water_km2": area_km2(prediction & valid, profile),
            "metrics": metrics(prediction, y, valid),
            "model_version": info["version"],
            "dataset_version": info["dataset_version"],
            "evaluation_scope": (
                "training_scene"
                if row["id"] in info["training_scene_ids"]
                else "validation_scene"
                if row["id"] in info.get("validation_scene_ids", [])
                else "held_out_scene"
                if row["event"] in info.get("training_event_ids", []) + info.get("validation_event_ids", [])
                else "held_out_event"
            ),
            "model_evaluation_scope": info["evaluation_scope"],
            "limitations": [
                info["warning"],
                "Surface water is not proof of new flooding.",
                "No historical-water subtraction, verified damage or emergency warning.",
                "Radar speckle, shadows and dark surfaces can cause errors.",
            ],
            "runtime_seconds": time.monotonic() - start,
            "downloads": {
                "geotiff": f"/api/v1/analyses/{analysis_id}/files/water-mask.tif",
                "metadata": f"/api/v1/analyses/{analysis_id}/files/result.json",
            },
            "overlay": f"/api/v1/analyses/{analysis_id}/files/prediction.png",
        }
        (output / "result.json").write_text(json.dumps(result, indent=2))
        with Session.begin() as db:
            db.add(Result(analysis_id=analysis_id, details=result))
            db.get(Analysis, analysis_id).status = "completed"
    except Exception:
        log.exception("Analysis failed: %s", analysis_id)
        with Session.begin() as db:
            job = db.get(Analysis, analysis_id)
            if job:
                job.status = "failed"
                job.error = "Analysis failed. Check server logs; input files or model may be unavailable."
