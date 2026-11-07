"""Validate raster pairs, render previews, and preserve georeferencing."""

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pyproj import Geod
from rasterio.warp import transform_bounds

NORMALIZATION = {
    "sensor": "Sentinel-1 GRD dB",
    "bands": ["VV", "VH"],
    "clip_db": [-30, 5],
}


def read_pair(image: Path, label: Path):
    with rasterio.open(image) as src, rasterio.open(label) as target:
        if src.count != 2 or target.count != 1:
            raise ValueError("Expected two Sentinel-1 channels and one label channel")
        if (
            src.crs is None
            or src.crs != target.crs
            or src.shape != target.shape
            or not src.transform.almost_equals(target.transform)
        ):
            raise ValueError("Image and label must have identical CRS, grid and dimensions")
        x, y = src.read().astype("float32"), target.read(1)
        if not np.isin(y, [-1, 0, 1]).all():
            raise ValueError("Unknown label encoding; expected -1, 0, 1")
        valid = (y >= 0) & np.isfinite(x).all(axis=0) & (src.read_masks() > 0).all(axis=0)
        return x, y, valid, src.profile.copy()


def normalize(x):
    return (np.clip(np.nan_to_num(x, nan=-30, posinf=5, neginf=-30), -30, 5) + 30) / 35


def metrics(prediction, label, valid):
    p, y = prediction[valid].astype(bool), label[valid].astype(bool)
    tp, fp, fn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum())

    def ratio(n, d):
        return n / d if d else None

    return {
        "iou": ratio(tp, tp + fp + fn),
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "dice": ratio(2 * tp, 2 * tp + fp + fn),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "valid_pixels": int(valid.sum()),
    }


def area_km2(mask, profile):
    """Geodesic pixel area; no assumption that degree-sized pixels are square metres."""
    if str(profile["crs"]) != "EPSG:4326":
        raise ValueError("Area calculation currently supports EPSG:4326 rasters only")
    t = profile["transform"]
    if t.b != 0 or t.d != 0:
        raise ValueError("Area calculation requires a north-up raster")
    geod, area = Geod(ellps="WGS84"), 0.0
    for row, count in enumerate(mask.sum(axis=1)):
        if not count:
            continue
        left, top = t.c, t.e * row + t.f
        right, bottom = t.a + t.c, t.e * (row + 1) + t.f
        a, _ = geod.polygon_area_perimeter([left, right, right, left], [top, top, bottom, bottom])
        area += abs(a) * int(count)
    return area / 1_000_000


def write_mask(path, prediction, valid, profile):
    profile = profile.copy()
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    profile.update(driver="GTiff", count=1, dtype="uint8", nodata=255, compress="deflate")
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.where(valid, prediction, 255).astype("uint8"), 1)
        dst.update_tags(
            classes="0=non-water,1=water,255=invalid",
            interpretation="detected surface water",
        )


def mask_preview(path, mask, valid, color=(24, 184, 240)):
    out = np.zeros((*mask.shape, 4), dtype="uint8")
    out[mask.astype(bool) & valid] = (*color, 180)
    Image.fromarray(out).save(path)


def prepare_scene(image, label, optical, output):
    output.mkdir(parents=True, exist_ok=True)
    x, y, valid, profile = read_pair(image, label)
    with rasterio.open(image) as src:
        bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
    radar = (normalize(x)[0] * 255).astype("uint8")
    Image.fromarray(radar).convert("RGB").save(output / "radar.png")
    if optical:
        with rasterio.open(optical) as src:
            if (
                src.crs != profile["crs"]
                or src.shape != y.shape
                or not src.transform.almost_equals(profile["transform"])
            ):
                raise ValueError("Optical imagery is not aligned")
            rgb = src.read([4, 3, 2]).astype("float32") / 10000
            rgb = np.clip(rgb / 0.3, 0, 1) ** (1 / 1.8)
            Image.fromarray((rgb.transpose(1, 2, 0) * 255).astype("uint8")).save(output / "optical.png")
    mask_preview(output / "label.png", y == 1, valid, (240, 177, 64))
    return {
        "bounds": list(bounds),
        "width": y.shape[1],
        "height": y.shape[0],
        "crs": str(profile["crs"]),
        "valid_pixels": int(valid.sum()),
        "label_counts": {str(i): int((y == i).sum()) for i in [-1, 0, 1]},
    }
