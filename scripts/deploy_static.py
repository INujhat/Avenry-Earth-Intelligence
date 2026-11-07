"""Upload a verified browser-only build to the owner's existing private static Space."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=ROOT / "frontend/browser-dist")
    args = parser.parse_args()
    folder = args.folder.resolve()
    catalog = json.loads((folder / "data/catalog.json").read_text())
    if not (folder / "index.html").is_file() or len(catalog["scenes"]) < 1:
        raise SystemExit("Build and export the browser app before upload")
    if any(p.stat().st_size > 4 * 1024 * 1024 for p in folder.rglob("*") if p.is_file()):
        raise SystemExit("Unexpected large asset; use bounded runtime chunks")
    if any(p.name.startswith(".env") or "node_modules" in p.parts for p in folder.rglob("*")):
        raise SystemExit("Unexpected build contents")
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is not configured")

    api = HfApi(token=token)
    if api.whoami().get("name", "").casefold() != "nujamred":
        raise SystemExit("The token must belong to NujAMred")
    repo = "NujAMred/avenry-earth-intelligence"
    info = api.space_info(repo)
    if info.sdk != "static" or not info.private:
        raise SystemExit("Expected the existing private static Space; refusing to change another deployment")
    (folder / "README.md").write_text("""---
title: Avenry Earth Intelligence
emoji: 🌍
colorFrom: green
colorTo: blue
sdk: static
app_file: index.html
---

# Avenry Earth Intelligence

Free browser-inference research application. Real U-Net predictions execute in
ONNX Runtime WebAssembly on your device, with no paid compute or Python backend
required for this hosted version. The original FastAPI backend remains in GitHub.

Eight real Sen1Floods11 scenes, georeferenced overlays, hand-label comparisons,
metrics, area estimates, persistent device history and GeoTIFF downloads.
The first analysis downloads the runtime and model. Keep the tab open while
analysis runs. Clearing browser storage removes local history and saved outputs.

This Space is private. The dataset's official STAC declares proprietary terms;
verify applicable rights before public redistribution. Surface water is not
verified flooding. Small pilot performance is weak and uneven; this is not an
emergency warning system.

Source: https://github.com/INujhat/Avenry-Earth-Intelligence/tree/avenry-working-app
""")
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/x-ndjson"}
    client = httpx.Client(timeout=60)

    binary_suffixes = {".bin", ".onnx", ".f32", ".f64", ".i8", ".u8", ".png", ".tif"}

    def send(files, message):
        items = [{"key": "header", "value": {"summary": message, "description": ""}}]
        for name, content in files:
            if Path(name).suffix in binary_suffixes:
                oid = hashlib.sha256(content).hexdigest()
                batch = client.post(
                    f"https://huggingface.co/spaces/{repo}.git/info/lfs/objects/batch",
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/vnd.git-lfs+json",
                    },
                    json={
                        "operation": "upload",
                        "transfers": ["basic"],
                        "hash_algo": "sha256",
                        "objects": [{"oid": oid, "size": len(content)}],
                    },
                )
                batch.raise_for_status()
                obj = batch.json()["objects"][0]
                if obj.get("error"):
                    raise SystemExit("Hugging Face rejected a binary asset; inspect repository access")
                actions = obj.get("actions", {})
                if "upload" in actions:
                    action = actions["upload"]
                    host = urlparse(action["href"]).hostname
                    if host != "hf-hub-lfs-us-east-1.s3-accelerate.amazonaws.com":
                        raise SystemExit(f"New storage hostname requires review: {host}")
                    try:
                        response = client.put(
                            action["href"], headers=action.get("header", {}), content=content
                        )
                        response.raise_for_status()
                    except httpx.HTTPError:
                        raise SystemExit(
                            f"Binary upload blocked or failed at {host}; enable its network access before retrying"
                        ) from None
                    if "verify" in actions:
                        verify = actions["verify"]
                        if urlparse(verify["href"]).hostname != "huggingface.co":
                            raise SystemExit("Unexpected binary verification hostname")
                        response = client.post(
                            verify["href"],
                            headers={**verify.get("header", {}), "Authorization": "Bearer " + token},
                            json={"oid": oid, "size": len(content)},
                        )
                        response.raise_for_status()
                items.append(
                    {
                        "key": "lfsFile",
                        "value": {"path": name, "algo": "sha256", "oid": oid, "size": len(content)},
                    }
                )
            else:
                items.append(
                    {
                        "key": "file",
                        "value": {
                            "path": name,
                            "encoding": "base64",
                            "content": base64.b64encode(content).decode(),
                        },
                    }
                )
        body = b"".join(json.dumps(item).encode() + b"\n" for item in items)
        response = client.post(
            f"https://huggingface.co/api/spaces/{repo}/commit/main", headers=headers, content=body
        )
        if response.is_error:
            print("Commit rejected:", response.text[:800], flush=True)
        response.raise_for_status()
        return response.json()

    attributes = "".join(
        f"*{suffix} filter=lfs diff=lfs merge=lfs -text\n" for suffix in sorted(binary_suffixes)
    )
    send([(".gitattributes", attributes.encode())], "Use supported LFS storage for binary assets")
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.name != "index.html")
    files.append(folder / "index.html")  # Publish the entry point after its assets.
    batches, batch, size = [], [], 0
    for path in files:
        if batch and size + path.stat().st_size > 3 * 1024 * 1024:
            batches.append(batch)
            batch, size = [], 0
        batch.append(path)
        size += path.stat().st_size
    if batch:
        batches.append(batch)
    for index, batch in enumerate(batches, 1):
        commit = send(
            [(str(p.relative_to(folder)), p.read_bytes()) for p in batch],
            f"Deploy browser application assets {index}/{len(batches)}",
        )
        print(f"Committed upload batch {index}/{len(batches)}", flush=True)
    client.close()
    # Print metadata only, never authentication or signed URLs.
    print("Static application uploaded to:", repo)
    print("Commit:", commit.get("commitOid"))
    report = {
        str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in folder.rglob("*")
        if p.is_file()
    }
    (ROOT / "docs/static-deployment-files.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
