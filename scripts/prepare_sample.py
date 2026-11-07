"""Fetch the three pinned official sample files, verify hashes, and create catalog."""

import hashlib
import json
import os
import urllib.request
from pathlib import Path

from ml.geospatial import prepare_scene

ROOT = Path(__file__).resolve().parents[1]
REVISION = "b9e460dabe70230111a3c3d36cd0c5ce03606ee9"


def main():
    os.chdir(ROOT)
    sources = json.loads((ROOT / "data/sample-sources.json").read_text())
    for entry in sources["files"]:
        path = ROOT / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            temp = path.with_suffix(".part")
            try:
                with (
                    urllib.request.urlopen(entry["url"], timeout=60) as response,
                    temp.open("wb") as out,
                ):
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > 20 * 1024 * 1024:
                            raise ValueError("Sample download exceeds 20 MB limit")
                        out.write(chunk)
                if hashlib.sha256(temp.read_bytes()).hexdigest() != entry["sha256"]:
                    raise ValueError("Downloaded sample checksum mismatch")
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Sample checksum mismatch: {path}")
    scene = {
        "id": "Spain_7370579",
        "name": "Lower Segura · Spain",
        "event": "Spain",
        "split": "demo",
        "radar": "data/raw/sample/S1/Spain_7370579_S1Hand.tif",
        "label": "data/raw/sample/Labels/Spain_7370579_LabelHand.tif",
        "optical": "data/raw/sample/S2/Spain_7370579_S2Hand.tif",
        "source": "Sen1Floods11 official repository sample",
        "source_revision": REVISION,
        "license_status": "No explicit license file found in source repository; verify terms before redistribution.",
        "s1_date": "2019-09-18",
        "s2_date": "2019-09-18",
    }
    metadata = (
        json.loads((ROOT / "data/raw/events.geojson").read_text())
        if (ROOT / "data/raw/events.geojson").exists()
        else None
    )
    if metadata:
        for feature in metadata["features"]:
            p = feature["properties"]
            if p["location"] == "Spain":
                scene["s1_date"], scene["s2_date"] = (
                    p["s1_date"].replace("/", "-"),
                    p["s2_date"].replace("/", "-"),
                )
    else:
        scene["s1_date"] = scene["s2_date"] = None
    scene.update(
        prepare_scene(
            Path(scene["radar"]),
            Path(scene["label"]),
            Path(scene["optical"]),
            ROOT / "data/processed" / scene["id"],
        )
    )
    manifest = {"version": f"sen1floods11-github-{REVISION[:12]}", "scenes": [scene]}
    (ROOT / "data/manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(scene, indent=2))


if __name__ == "__main__":
    main()
