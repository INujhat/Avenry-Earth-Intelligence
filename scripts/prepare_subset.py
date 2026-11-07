"""Download a bounded, event-disjoint research subset from the official public bucket.

Uses official split manifests as an inventory, then deliberately reassigns whole
countries/events to disjoint sets. This is NOT the official benchmark split.
No full-bucket sync is performed. Requires storage.googleapis.com network access.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path

from ml.geospatial import prepare_scene

BASE = "https://storage.googleapis.com/sen1floods11/v1.1"
ROOT = Path(__file__).resolve().parents[1]


def fetch(url, destination, limit=20 * 1024 * 1024):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination.read_bytes()
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Unexpectedly large dataset file")
    temp = destination.with_suffix(".part")
    temp.write_bytes(content)
    temp.replace(destination)
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chips-per-event", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.chips_per_event <= 4:
        parser.error("Use 1–4 chips per event; this command only prepares a small subset")
    metadata_bytes = fetch(f"{BASE}/Sen1Floods11_Metadata.geojson", ROOT / "data/raw/events.geojson")
    metadata = {f["properties"]["location"]: f["properties"] for f in json.loads(metadata_bytes)["features"]}
    inventory = set()
    for split in ["train", "valid", "test"]:
        relative = f"splits/flood_handlabeled/flood_{split}_data.csv"
        content = fetch(f"{BASE}/{relative}", ROOT / "data/raw/splits" / Path(relative).name)
        for row in csv.reader(io.StringIO(content.decode())):
            for field in row:
                match = re.fullmatch(r"([A-Za-z]+_\d+)_S1Hand\.tif", Path(field.strip()).name)
                if match:
                    inventory.add(match[1])
    events = sorted({chip.split("_")[0] for chip in inventory if not chip.startswith("Spain_")})
    if len(events) < 4:
        raise ValueError(
            "Expected at least four non-Spain events in official manifests; inspect source format"
        )
    assignment = {events[0]: "train", events[1]: "train", events[2]: "validation", events[3]: "test"}
    scenes, files = [], []
    for event, split in assignment.items():
        chips = sorted(chip for chip in inventory if chip.split("_")[0] == event)[: args.chips_per_event]
        for chip in chips:
            paths = {}
            for layer in ["S1Hand", "LabelHand", "S2Hand"]:
                relative = f"data/flood_events/HandLabeled/{layer}/{chip}_{layer}.tif"
                path = ROOT / "data/raw/subset" / layer / f"{chip}_{layer}.tif"
                payload = fetch(f"{BASE}/{relative}", path)
                files.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "url": f"{BASE}/{relative}",
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                )
                paths[layer] = path
            details = prepare_scene(
                paths["S1Hand"], paths["LabelHand"], paths["S2Hand"], ROOT / "data/processed" / chip
            )
            scenes.append(
                {
                    "id": chip,
                    "name": f"{event} · {chip.split('_')[1]}",
                    "event": event,
                    "split": split,
                    "radar": str(paths["S1Hand"].relative_to(ROOT)),
                    "label": str(paths["LabelHand"].relative_to(ROOT)),
                    "optical": str(paths["S2Hand"].relative_to(ROOT)),
                    "s1_date": metadata.get(event, {}).get("s1_date", "").replace("/", "-") or None,
                    "s2_date": metadata.get(event, {}).get("s2_date", "").replace("/", "-") or None,
                    "source": "Sen1Floods11 v1.1 official public bucket",
                    "license_status": "Official STAC collection declares proprietary; obtain applicable rights before redistribution.",
                    **details,
                }
            )
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    manifest = {
        "version": f"sen1floods11-v1.1-subset-{digest[:12]}",
        "split_policy": "First four alphabetically sorted non-Spain events: two train, one validation, one test. Not official benchmark splits.",
        "events": assignment,
        "scenes": scenes,
        "files": files,
    }
    destination = ROOT / "data/subset-manifest.json"
    destination.write_text(json.dumps(manifest, indent=2))
    print(
        f"Prepared {len(scenes)} real scenes at {destination}. Inspect before training; demo catalog unchanged."
    )


if __name__ == "__main__":
    main()
