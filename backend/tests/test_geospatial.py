import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ml.geospatial import area_km2, metrics, normalize, read_pair, write_mask


def raster(path, array, transform=None):
    if array.ndim == 2:
        array = array[None]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[1],
        width=array.shape[2],
        count=array.shape[0],
        dtype=array.dtype,
        crs="EPSG:4326",
        transform=transform or from_origin(0, 1, 0.0001, 0.0001),
    ) as dst:
        dst.write(array)


def test_alignment_and_invalid_pixels(tmp_path):
    x = np.ones((2, 4, 4), dtype="float32")
    x[:, 0, 0] = np.nan
    y = np.zeros((4, 4), dtype="int16")
    y[1, 1] = -1
    raster(tmp_path / "x.tif", x)
    raster(tmp_path / "y.tif", y)
    _, _, valid, profile = read_pair(tmp_path / "x.tif", tmp_path / "y.tif")
    assert valid.sum() == 14
    write_mask(tmp_path / "out.tif", np.ones((4, 4), dtype=bool), valid, profile)
    with rasterio.open(tmp_path / "out.tif") as out:
        assert out.nodata == 255 and out.crs.to_epsg() == 4326
        assert out.transform == profile["transform"]
        assert (out.read(1) == 255).sum() == 2


def test_rejects_misaligned_pair(tmp_path):
    raster(tmp_path / "x.tif", np.ones((2, 4, 4), dtype="float32"))
    raster(tmp_path / "y.tif", np.zeros((4, 4), dtype="int16"), from_origin(2, 3, 0.01, 0.01))
    with pytest.raises(ValueError, match="identical CRS"):
        read_pair(tmp_path / "x.tif", tmp_path / "y.tif")


def test_unknown_labels_rejected(tmp_path):
    raster(tmp_path / "x.tif", np.ones((2, 4, 4), dtype="float32"))
    raster(tmp_path / "y.tif", np.full((4, 4), 2, dtype="int16"))
    with pytest.raises(ValueError, match="encoding"):
        read_pair(tmp_path / "x.tif", tmp_path / "y.tif")


def test_metrics_ignore_invalid_and_handle_undefined():
    p = np.array([1, 1, 0, 1], dtype=bool)
    y = np.array([1, 0, 1, -1])
    m = metrics(p, y, y >= 0)
    assert m["iou"] == pytest.approx(1 / 3)
    assert m["precision"] == m["recall"] == m["dice"] == 0.5
    assert metrics(p, y, np.zeros(4, dtype=bool))["iou"] is None


def test_geodesic_area_and_normalization():
    profile = {"crs": "EPSG:4326", "transform": from_origin(0, 1, 0.0001, 0.0001)}
    one = area_km2(np.ones((1, 1), dtype=bool), profile)
    assert 0.00012 < one < 0.00013
    assert area_km2(np.zeros((2, 2), dtype=bool), profile) == 0
    assert area_km2(np.ones((1, 2), dtype=bool), profile) == pytest.approx(2 * one)
    normalized = normalize(np.array([np.nan, -100, -30, 5, 100], dtype="float32"))
    assert np.isfinite(normalized).all()
    assert normalized.tolist() == [0, 0, 0, 1, 1]
