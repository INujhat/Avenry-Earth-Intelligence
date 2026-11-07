"""Compare an actual browser GeoTIFF and JSON download to the Python reference."""

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
import torch

from ml.geospatial import area_km2, metrics, normalize, read_pair
from ml.model import UNet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mask", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.metadata.read_text())
    manifest = json.loads(Path("data/manifest.json").read_text())
    scene = next(r for r in manifest["scenes"] if r["id"] == result["scene_id"])
    x, y, valid, profile = read_pair(Path(scene["radar"]), Path(scene["label"]))
    model = UNet()
    model.load_state_dict(
        torch.load("artifacts/baseline/model.pt", map_location="cpu", weights_only=True)["state_dict"]
    )
    model.eval()
    torch.set_num_threads(2)
    with torch.inference_mode():
        prediction = model(torch.from_numpy(normalize(x)[None]))[0, 0].numpy() >= 0
    with rasterio.open(args.mask) as mask:
        assert mask.crs == profile["crs"] and mask.transform == profile["transform"] and mask.nodata == 255
        assert np.array_equal(mask.read(1), np.where(valid, prediction, 255).astype("uint8"))
    for key, value in metrics(prediction, y, valid).items():
        assert result["metrics"][key] == value, key
    assert abs(result["detected_water_km2"] - area_km2(prediction & valid, profile)) < 1e-8
    print("PASS browser prediction pixels, metrics, area, CRS, affine transform and nodata match Python")


if __name__ == "__main__":
    main()
