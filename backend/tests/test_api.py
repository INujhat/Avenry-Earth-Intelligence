"""Use a temporary database; real sample inference is explicitly marked integration."""

import time
from uuid import uuid4

import pytest
import rasterio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import db as database
from backend.app import main
from backend.app.services import catalog, inference


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    sessions = sessionmaker(engine, expire_on_commit=False)
    database.Base.metadata.create_all(engine)
    for module in [main, catalog, inference]:
        monkeypatch.setattr(module, "Session", sessions)
    monkeypatch.setattr(main.command, "upgrade", lambda *a: None)
    with TestClient(main.app) as client:
        yield client
    engine.dispose()


def test_api_errors_are_consistent(client):
    assert client.get("/api/v1/scenes/no-such-scene").status_code == 404
    assert client.get("/api/v1/scenes?bbox=0,0,0,0").status_code == 422
    assert client.get("/api/v1/analyses/not-a-uuid").status_code == 422
    assert client.get(f"/api/v1/analyses/{uuid4()}").status_code == 404
    response = client.post("/api/v1/analyses", json={"scene_id": "../../etc/passwd"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert client.post("/api/v1/analyses", json={"scene_id": "absent"}).status_code == 404


def test_real_sample_analysis_and_geotiff(client, tmp_path):
    scenes = client.get("/api/v1/scenes").json()["items"]
    if not scenes or not client.get("/api/v1/system").json()["model_ready"]:
        pytest.skip("Run sample preparation and demo training to enable real-data integration")
    scene = scenes[0]
    assert client.get(f"/api/v1/scenes/{scene['id']}/assets/optical").headers["content-type"] == "image/png"
    response = client.post("/api/v1/analyses", json={"scene_id": scene["id"]})
    assert response.status_code == 202
    job = response.json()
    for _ in range(150):
        current = client.get(f"/api/v1/analyses/{job['id']}").json()
        if current["status"] in ["completed", "failed"]:
            break
        time.sleep(0.1)
    assert current["status"] == "completed", current
    result = client.get(f"/api/v1/analyses/{job['id']}/results").json()
    assert result["interpretation"] == "detected_surface_water"
    assert result["evaluation_scope"] in {
        "training_scene",
        "held_out_event",
        "validation_scene",
        "held_out_scene",
    }
    assert result["metrics"]["valid_pixels"] == scene["valid_pixels"]
    assert result["detected_water_km2"] > 0
    geotiff = client.get(result["downloads"]["geotiff"])
    assert geotiff.status_code == 200
    path = tmp_path / "mask.tif"
    path.write_bytes(geotiff.content)
    with rasterio.open(path) as mask:
        assert mask.crs.to_epsg() == 4326
        assert mask.shape == (scene["height"], scene["width"])
        assert mask.nodata == 255
        assert set(mask.read(1).ravel()) <= {0, 1, 255}
    assert client.get(result["overlay"]).status_code == 200
    assert client.get(result["downloads"]["metadata"]).json()["analysis_id"] == job["id"]
    assert client.get(f"/api/v1/analyses/{job['id']}/files/secret.env").status_code == 422
    assert len(client.get("/api/v1/analyses").json()["items"]) == 1


def test_worker_failure_is_recorded(client, monkeypatch):
    if not client.get("/api/v1/scenes").json()["items"] or not catalog.model_info():
        pytest.skip("Sample/model not installed")

    def unavailable(*args, **kwargs):
        raise ValueError("Simulated missing file")

    monkeypatch.setattr(inference, "read_pair", unavailable)
    response = client.post(
        "/api/v1/analyses", json={"scene_id": client.get("/api/v1/scenes").json()["items"][0]["id"]}
    )
    assert response.status_code == 202
    for _ in range(50):
        job = client.get("/api/v1/analyses/" + response.json()["id"]).json()
        if job["status"] == "failed":
            break
        time.sleep(0.1)
    assert job["status"] == "failed"
    assert client.get("/api/v1/analyses/" + job["id"] + "/results").status_code == 409
