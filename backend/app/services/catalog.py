"""Register verified local scenes and model metadata."""

import hashlib
import json

from sqlalchemy import text

from backend.app.config import ARTIFACTS, DATA, ROOT
from backend.app.db import ModelVersion, Provenance, Region, Scene, Session


def local_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(DATA):
        raise ValueError("Catalog paths must stay inside the configured data directory")
    return path


def model_info():
    metadata_path = ARTIFACTS / "model.json"
    checkpoint = ARTIFACTS / "model.pt"
    if not metadata_path.exists() or not checkpoint.exists():
        return None
    info = json.loads(metadata_path.read_text())
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != info["checkpoint_sha256"]:
        raise ValueError("Model checkpoint checksum mismatch")
    return info


def sync_catalog():
    manifest_path = DATA / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text())
    with Session.begin() as db:
        db.merge(
            Provenance(
                id=manifest["version"],
                details={
                    "version": manifest["version"],
                    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                },
            )
        )
        for row in manifest["scenes"]:
            for key in ["radar", "label", "optical"]:
                if row.get(key) and not local_path(row[key]).is_file():
                    raise ValueError(f"Missing scene file: {row['id']} / {key}")
            db.merge(Region(id=row["event"], name=row["event"], bounds=row["bounds"]))
            db.merge(
                Scene(
                    id=row["id"],
                    region_id=row["event"],
                    dataset_id=manifest["version"],
                    details=row,
                )
            )
            if db.bind.dialect.name == "postgresql":
                db.flush()
                west, south, east, north = row["bounds"]
                db.execute(
                    text("UPDATE regions SET footprint = ST_MakeEnvelope(:w,:s,:e,:n,4326) WHERE id=:id"),
                    {"w": west, "s": south, "e": east, "n": north, "id": row["event"]},
                )
        info = model_info()
        if info:
            db.merge(ModelVersion(id=info["version"], details=info))


def public_scene(scene):
    return {k: v for k, v in scene.details.items() if k not in {"radar", "label", "optical"}} | {
        "dataset_version": scene.dataset_id,
        "assets": {
            kind: f"/api/v1/scenes/{scene.id}/assets/{kind}" for kind in ["radar", "optical", "label"]
        },
    }
