"""Unit tests for real change calculations; pip install numpy rasterio pytest."""
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "change_detection"))
from analyze import analyze


def mask(path, data, transform=None):
    transform = transform or from_origin(500000, 1000000, 10, 10)
    with rasterio.open(path, "w", driver="GTiff", width=4, height=4, count=1,
                       dtype="uint8", crs="EPSG:32632", transform=transform, nodata=255) as dst:
        dst.write(np.array(data, dtype=np.uint8), 1)


def test_gain_loss_and_invalid(tmp_path):
    before = tmp_path / "before.tif"
    after = tmp_path / "after.tif"
    mask(before, [[0, 1, 255, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    mask(after, [[1, 0, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    result = analyze(before, after, tmp_path / "out")
    assert result["water_gained_km2"] == pytest.approx(0.0001)
    assert result["water_lost_km2"] == pytest.approx(0.0001)
    assert result["invalid_pixels"] == 1
    assert (tmp_path / "out" / "provenance.json").exists()
    assert (tmp_path / "out" / "water_change.geojson").exists()


def test_misaligned_grid_rejected(tmp_path):
    before = tmp_path / "before.tif"
    after = tmp_path / "after.tif"
    data = np.zeros((4, 4), dtype=np.uint8)
    mask(before, data)
    mask(after, data, from_origin(500010, 1000000, 10, 10))
    with pytest.raises(ValueError, match="identical"):
        analyze(before, after, tmp_path / "out")
