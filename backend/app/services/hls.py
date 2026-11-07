"""NASA CMR search and explicit optical-band preparation; never radar-model inference."""

from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import httpx
import numpy as np
import rasterio
from PIL import Image

CMR = "https://cmr.earthdata.nasa.gov/search"
HEADERS = {"User-Agent": "Avenry-AI-research/0.2"}


def search_hls(bbox: list[float], start: date, end: date, sensor="HLSS30", limit=5):
    if sensor not in {"HLSS30", "HLSL30"}:
        raise ValueError("Choose HLSS30 or HLSL30")
    if len(bbox) != 4 or not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
        raise ValueError("Invalid WGS84 bounding box")
    if start > end or not 1 <= limit <= 20:
        raise ValueError("Invalid date range or limit (1–20)")
    with httpx.Client(timeout=30, headers=HEADERS) as client:
        collection = client.get(
            f"{CMR}/collections.json", params={"short_name": sensor, "version": "2.0", "page_size": 1}
        )
        collection.raise_for_status()
        entries = collection.json()["feed"]["entry"]
        if not entries:
            raise ValueError("NASA CMR returned no HLS v2 collection")
        response = client.get(
            f"{CMR}/granules.json",
            params={
                "collection_concept_id": entries[0]["id"],
                "bounding_box": ",".join(map(str, bbox)),
                "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
                "page_size": limit,
            },
        )
        response.raise_for_status()
    return {
        "sensor": sensor,
        "version": "2.0",
        "inference_compatible": False,
        "items": [
            {
                "id": g["producer_granule_id"],
                "start": g.get("time_start"),
                "boxes": g.get("boxes", []),
                "links": [
                    link["href"]
                    for link in g.get("links", [])
                    if link.get("href", "").startswith("https://") and not link.get("inherited")
                ],
                "cloud_cover": g.get("cloud_cover"),
            }
            for g in response.json()["feed"]["entry"]
        ],
    }


def download_asset(url: str, destination: Path, token: str):
    """Download a selected NASA asset with bounded size and no redirect credential leakage."""
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "data.lpdaac.earthdatacloud.nasa.gov"
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Only HTTPS LP DAAC Earthdata Cloud assets are supported")
    if not token:
        raise ValueError("EARTHDATA_TOKEN is required for this selected data download")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(".part")
    try:
        with httpx.stream(
            "GET",
            url,
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=60,
            follow_redirects=False,
        ) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError("Unexpected redirect; use the authenticated direct LP DAAC asset URL")
            total = 0
            with temp.open("wb") as out:
                for chunk in response.iter_bytes(1024 * 1024):
                    total += len(chunk)
                    if total > 1024 * 1024 * 1024:
                        raise ValueError("Asset exceeds 1 GiB download limit")
                    out.write(chunk)
        with rasterio.open(temp) as dataset:
            if dataset.crs is None:
                raise ValueError("Downloaded asset is not georeferenced")
        temp.replace(destination)
    finally:
        temp.unlink(missing_ok=True)


def preview_hls(red: Path, green: Path, blue: Path, fmask: Path, destination: Path):
    """Apply HLS v2 Fmask bits and reflectance scaling to selected compatible bands."""
    with rasterio.open(fmask) as qa:
        quality = qa.read(1)
        # Bits 0..4: cirrus, cloud, adjacent cloud, cloud shadow, snow/ice.
        # Bit 5 is water: it must NOT be excluded. Bits 6..7 encode aerosol level.
        valid = (quality != 255) & ((quality & 31) == 0)
        channels = []
        for path in [red, green, blue]:
            with rasterio.open(path) as band:
                if (
                    band.crs != qa.crs
                    or band.shape != qa.shape
                    or not band.transform.almost_equals(qa.transform)
                ):
                    raise ValueError("HLS bands and Fmask are not on the same grid")
                values = band.read(1)
                valid &= (values != -9999) & (band.read_masks(1) > 0)
                channels.append(values.astype("float32") * 0.0001)
        rgb = np.clip(np.stack(channels, axis=-1) / 0.3, 0, 1) ** (1 / 1.8)
        rgba = np.dstack([(rgb * 255).astype("uint8"), valid.astype("uint8") * 255])
        destination.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba).save(destination)
        return {
            "crs": str(qa.crs),
            "bounds": list(qa.bounds),
            "valid_pixels": int(valid.sum()),
            "inference_enabled": False,
            "reason": "Optical HLS bands are incompatible with this two-band radar U-Net.",
        }
