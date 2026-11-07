#!/usr/bin/env bash
# Prepare the event-disjoint local research application from the repository root.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]]; then
  .venv/bin/python -m pip install -r requirements-cpu.txt
else
  .venv/bin/python -m pip install -r requirements-ml.txt
fi
.venv/bin/python -m pip check
if [[ ! -f data/manifest.json ]]; then
  .venv/bin/python -m scripts.prepare_subset
  cp data/subset-manifest.json data/manifest.json
fi
if [[ ! -f artifacts/baseline/model.pt || ! -f artifacts/baseline/model.json ]]; then
  .venv/bin/python -m ml.train --epochs 35
fi
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python -m pytest -q
