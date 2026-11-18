"""Reproducible two-date raster change analysis for Avenry.

Inputs are *already georeferenced binary water masks* (0=not water, 1=water,
255=invalid). This module does NOT infer water from raw Sentinel-1 GRD scenes.
Requires rasterio, numpy. Both masks must have matching CRS/grid; refusing
mismatched grids avoids false area and exposure calculations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(before: Path, after: Path, output: Path) -> dict:
    with rasterio.open(before) as a, rasterio.open(after) as b:
        if not a.crs or not b.crs or a.crs != b.crs or a.transform != b.transform or a.shape != b.shape:
            raise ValueError("Input masks require identical, non-null CRS, transform and shape; reproject first.")
        if a.count != 1 or b.count != 1:
            raise ValueError("Expected single-band binary masks.")
        if not a.crs.is_projected:
            raise ValueError("Area calculation requires an appropriate projected metric CRS.")
        if a.crs.linear_units not in ("metre", "meter", "metres", "meters"):
            raise ValueError("Projected CRS must use metre units for square-kilometre calculations.")
        x, y = a.read(1), b.read(1)
        valid = ((x == 0) | (x == 1)) & ((y == 0) | (y == 1))
        valid &= (a.read_masks(1) > 0) & (b.read_masks(1) > 0)
        gained = valid & (x == 0) & (y == 1)
        lost = valid & (x == 1) & (y == 0)
        unchanged_water = valid & (x == 1) & (y == 1)
        pixel_area = abs(a.transform.a * a.transform.e - a.transform.b * a.transform.d)
        if pixel_area <= 0:
            raise ValueError("Invalid pixel area.")
        change = np.full(x.shape, 255, dtype=np.uint8)
        change[valid] = 0
        change[gained] = 1
        change[lost] = 2
        profile = a.profile.copy()
        profile.update(driver="GTiff", dtype="uint8", count=1, nodata=255, compress="deflate", tiled=True)
        output.mkdir(parents=True, exist_ok=True)
        raster_path = output / "water_change.tif"
        with rasterio.open(raster_path, "w", **profile) as dst:
            dst.write(change, 1)
            dst.update_tags(1, class_0="unchanged", class_1="water_gained", class_2="water_lost", nodata_255="invalid")
            levels = [2, 4, 8, 16]
            from rasterio.enums import Resampling
            dst.build_overviews(levels, Resampling.nearest)
            dst.update_tags(ns="rio_overview", resampling="nearest")
        features = []
        for mask, label in ((gained, "water_gained"), (lost, "water_lost")):
            for geometry, value in shapes(mask.astype(np.uint8), mask=mask, transform=a.transform):
                if value != 1:
                    continue
                features.append({"type": "Feature", "geometry": transform_geom(a.crs, "EPSG:4326", geometry), "properties": {"change": label}})
        geojson = {"type": "FeatureCollection", "features": features}
        (output / "water_change.geojson").write_text(json.dumps(geojson))
        result = {
            "schema": "avenry.water-change.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input_before": {"filename": before.name, "sha256": sha256(before)},
            "input_after": {"filename": after.name, "sha256": sha256(after)},
            "crs": str(a.crs),
            "pixel_area_m2": pixel_area,
            "valid_pixels": int(valid.sum()),
            "invalid_pixels": int((~valid).sum()),
            "water_gained_km2": float(gained.sum() * pixel_area / 1_000_000),
            "water_lost_km2": float(lost.sum() * pixel_area / 1_000_000),
            "unchanged_water_km2": float(unchanged_water.sum() * pixel_area / 1_000_000),
            "output_raster": raster_path.name,
            "output_geojson": "water_change.geojson",
            "limitations": [
                "Changes are derived from supplied binary water masks, not raw satellite acquisitions.",
                "Water change does not establish flooding, risk, damage, or human exposure.",
                "Area accuracy depends on georeferencing, mask quality and projection.",
                "No confidence intervals are available without model probabilities and validation."
            ]
        }
        (output / "provenance.json").write_text(json.dumps(result, indent=2))
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.before, args.after, args.output), indent=2))
