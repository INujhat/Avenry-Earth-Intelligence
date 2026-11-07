import numpy as np
import pytest

from backend.app.services.hls import download_asset, preview_hls
from backend.tests.test_geospatial import raster


def test_fmask_excludes_cloud_and_fill_but_keeps_water(tmp_path):
    for name in ["red", "green", "blue"]:
        raster(tmp_path / f"{name}.tif", np.full((2, 2), 1500, dtype="int16"))
    raster(tmp_path / "qa.tif", np.array([[0, 2], [32, 255]], dtype="uint8"))
    result = preview_hls(
        *(tmp_path / f"{n}.tif" for n in ["red", "green", "blue", "qa"]), tmp_path / "rgb.png"
    )
    assert result["valid_pixels"] == 2
    assert result["inference_enabled"] is False
    from PIL import Image

    rgba = np.array(Image.open(tmp_path / "rgb.png"))
    assert rgba[:, :, 3].tolist() == [[255, 0], [255, 0]]


def test_download_rejects_untrusted_hosts_before_authentication(tmp_path):
    with pytest.raises(ValueError, match="Only HTTPS"):
        download_asset("https://example.com/data.tif", tmp_path / "output.tif", "not-a-real-token")
    with pytest.raises(ValueError, match="EARTHDATA_TOKEN"):
        download_asset("https://data.lpdaac.earthdatacloud.nasa.gov/file.tif", tmp_path / "output.tif", "")
