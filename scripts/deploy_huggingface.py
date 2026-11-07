"""Prepare source-only Docker Space and deploy with a securely configured HF_TOKEN."""

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {"Dockerfile", ".dockerignore", "alembic.ini"}
PREFIXES = {"backend", "ml", "scripts", "frontend"}


def prepare(destination: Path):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Deployment destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"]).decode().split("\0")
    count = 0
    for name in filter(None, tracked):
        path = Path(name)
        if not (
            name in FILES
            or path.parts[0] in PREFIXES
            or re.fullmatch(r"requirements(?:-[a-z]+)?\.txt", name)
            or name == "data/sample-sources.json"
        ):
            continue
        if path.suffix in {".tif", ".pt", ".db", ".png", ".jpg"} or ".env" in path.name:
            raise ValueError(f"Unexpected data/secret file in deployment inventory: {name}")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        count += 1
    dockerfile = destination / "Dockerfile"
    text = dockerfile.read_text().replace("EXPOSE 8000", "EXPOSE 7860")
    text = text.replace("USER terrasense", "ENV PORT=7860 AVENRY_BOOTSTRAP_DATA=1\nUSER terrasense")
    text = text.replace("http://127.0.0.1:8000/health", "http://127.0.0.1:7860/health")
    dockerfile.write_text(text)
    (destination / "README.md").write_text("""---
title: Avenry Earth Intelligence
emoji: 🌍
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
startup_duration_timeout: 1h
---

# Avenry Earth Intelligence

Real satellite surface-water research application: React, FastAPI, MapLibre and
CPU PyTorch. First startup fetches eight real scenes and trains a small U-Net.
It can take several minutes. Free CPU hosting may sleep and local storage is
not guaranteed to persist through rebuilds/restarts. No paid hardware is requested.

The initial Space is private. Sen1Floods11 STAC declares proprietary source terms;
obtain applicable rights before publicly redistributing imagery or learned artifacts.
No data, checkpoints, credentials or screenshots are uploaded in this source package.
Outputs detect surface water, not verified flooding or emergency warnings.

Source: https://github.com/INujhat/Avenry-Earth-Intelligence/tree/avenry-working-app
""")
    return count


def deploy(username, space):
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is missing. Add it securely in environment settings, not in chat.")
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    identity = api.whoami()
    if identity.get("name", "").casefold() != username.casefold():
        raise SystemExit("The configured HF_TOKEN belongs to a different account; deployment stopped.")
    with tempfile.TemporaryDirectory(prefix="avenry-space-") as folder:
        prepare(Path(folder))
        repo_id = f"{username}/{space}"
        # Fail on an existing name rather than overwrite an unknown Space.
        api.create_repo(
            repo_id,
            repo_type="space",
            space_sdk="docker",
            private=True,
            exist_ok=False,
            space_hardware="cpu-basic",
        )
        api.upload_folder(
            folder_path=folder,
            repo_id=repo_id,
            repo_type="space",
            commit_message="Deploy Avenry Earth Intelligence CPU research app",
        )
        print("Space source uploaded:", api.space_info(repo_id).id)
        print("Build and live inference still need validation before calling the website ready.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="NujAMred")
    parser.add_argument("--space", default="avenry-earth-intelligence")
    parser.add_argument("--prepare-only", type=Path)
    args = parser.parse_args()
    if not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", v) for v in [args.username, args.space]):
        parser.error("Invalid account or Space name")
    if args.prepare_only:
        print(f"Prepared {prepare(args.prepare_only)} source files; no upload performed")
    else:
        deploy(args.username, args.space)


if __name__ == "__main__":
    main()
