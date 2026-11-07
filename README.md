# Avenry Earth Intelligence

**Earth intelligence, with evidence you can inspect.**

A local satellite-analysis research application: browse real imagery, run a small
trained U-Net, inspect georeferenced surface-water predictions, compare hand labels,
and download GeoTIFF masks and result metadata. React + TypeScript + MapLibre,
FastAPI + PyTorch + Rasterio, SQLite or PostgreSQL/PostGIS.

**Current status:** real imagery, trained U-Net, event-disjoint pilot evaluation,
map overlays, job history and georeferenced downloads are implemented. The pilot
uses eight scenes: Ghana/India for training, Mekong for validation and Nigeria
for testing. NASA scene search has also succeeded; protected HLS downloads still
require your Earthdata credentials. This is a research prototype, not a verified
flood warning service. No permanently public hosted deployment exists.

## What you can do

- Browse the verified Sen1Floods11 Spain scene and acquisition metadata.
- Explore optical imagery or VV radar on an interactive map with scene footprint,
  coordinates and scale. No paid basemap or API key required.
- Submit a real PyTorch analysis; see queued/running/completed/failed status.
- Toggle water prediction and reference-label overlays and adjust opacity.
- Inspect geodesic detected-water area, IoU, precision, recall and F1/Dice.
- Download a georeferenced water mask (`0` non-water, `1` water, `255` invalid)
  and JSON metadata with model/dataset versions and limitations.
- Reopen persistent analysis history and inspect the methodology.

Detected surface water is **not automatically new flooding**. There is no
historical-water subtraction, verified damage, road closure or population estimate.
This is not an emergency warning system.

## Open the website in your browser using GitHub Codespaces

The complete source is on the `avenry-working-app` branch. You do not need to install Python, Node or Docker on your Mac for this option.

1. Open this project's `avenry-working-app` branch on GitHub.
2. Click **Code → Codespaces → Create codespace on avenry-working-app**.
3. Wait for the setup task to finish. It installs dependencies, downloads the
   bounded eight-scene subset, trains the pilot model, builds the website and
   runs the tests. The first setup takes several minutes.
4. The website should open automatically. Otherwise choose the **Ports** tab and
   click **Open in Browser** beside port **8000**, labeled
   **Avenry Earth Intelligence website**.

That forwarded **HTTPS address** is the actual website for your running Codespace.
A `/workspace/...` path is not a web address. The website stops when the Codespace
stops; keep the port private. GitHub Codespaces requires your GitHub account and
uses its compute/storage allowance. Check your allowance before starting; do not
select paid resources if you want to stay within a free allowance.

The configuration is in `.devcontainer/`. Its setup and startup commands have
been exercised in the cloud workspace; provisioning an actual Codespace still
requires your GitHub account. It is not a permanently public hosted deployment.

## Run on your Mac (Apple M2)

These files are in the Codex workspace at `/workspace/Avenry-Earth-Intelligence`.
For the current implementation, use the `avenry-working-app` GitHub branch,
or the delivered source bundle. Open Terminal in the project directory.

First check tools:

```bash
sw_vers
uname -m
python3 --version
git --version
node --version
npm --version
df -h .
```

Expected: macOS, `arm64`, Python 3.12, Node 22+ (Node 22 or 24 recommended), and
working Git/npm. This cloud build was checked on Linux x86_64, not your Mac.
Use a Python 3.12 installation and current Node LTS from official sources if needed.
Allow roughly 4 GB disk space and 4 GB memory for dependencies/building. CPU
inference needs no GPU; the tiny demo trains with two CPU threads.

To obtain the code on your Mac:

```bash
git clone --branch avenry-working-app https://github.com/INujhat/Avenry-Earth-Intelligence.git
cd Avenry-Earth-Intelligence
```

From the project directory:

```bash
bash scripts/bootstrap.sh
bash scripts/start.sh
```

The bootstrap installs dependencies in `.venv`, downloads the bounded real-data subset
if needed, trains an event-disjoint pilot checkpoint if absent, builds the website and
runs tests. It preserves an existing catalog/checkpoint. First-time setup needs
Internet access; an initialized application can run offline.

The server should print `Application startup complete`. On **your own Mac**, open
`http://127.0.0.1:8000` in your browser. This loopback address is not a public site
and does not provide a link to the Codex cloud machine. Select **Explore scene**,
then **Run water analysis**. Wait for **Analysis complete**, inspect layers and
choose **Download GeoTIFF**. Stop the server with Ctrl+C.

In a second terminal, verify the live workflow:

```bash
.venv/bin/python -m scripts.smoke
```

Expected: `PASS health/catalog/job/results/GeoTIFF`, an actual job ID, area and
the actual evaluation scope. This creates a real analysis record.

## Individual development commands

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Mac / Apple Silicon:
python -m pip install -r requirements-ml.txt
# Linux x86_64 CPU-only alternative (use instead of the preceding ML command):
# python -m pip install -r requirements-cpu.txt
python -m scripts.prepare_sample
python -m ml.train --demo --epochs 35
npm ci --prefix frontend
npm run build --prefix frontend
python -m pytest -q
python -m ruff check backend ml scripts
python -m ruff format --check backend ml scripts
bash scripts/start.sh
```

For frontend hot reload, run `npm run dev --prefix frontend` in another terminal
while the backend runs on port 8000. Vite proxies API calls to it. The production
build is served directly by FastAPI; no separate frontend server is needed then.

## API

Interactive documentation: `/docs`; machine-readable schema: `/openapi.json`.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | API process availability |
| `GET /api/v1/system` | Checkpoint availability and training provenance |
| `GET /api/v1/scenes` | Scene catalog; optional `bbox=west,south,east,north` |
| `GET /api/v1/scenes/{id}` | Scene metadata and preview assets |
| `POST /api/v1/analyses` | Submit `{"scene_id":"Spain_7370579"}`; returns 202 |
| `GET /api/v1/analyses` | Recent persistent jobs |
| `GET /api/v1/analyses/{id}` | Job status or safe error |
| `GET /api/v1/analyses/{id}/results` | Completed results and download paths |

The local worker accepts at most four pending jobs. Keep one API process.
Interrupted jobs are marked failed on restart. Missing scenes return 404, malformed
inputs 422, unavailable results/model 409, and a full queue 429.

## Model and actual measurements

A two-level U-Net takes Sentinel-1 VV/VH dB inputs, clipped to −30…5 and scaled
to 0…1. Training uses valid-label binary cross-entropy, Adam, deterministic CPU
operations, 128×128 patches, seed 42 and 35 epochs. Checkpoints are checksum-verified.
The pipeline includes validation and event-disjoint test support; it refuses to
use the demo split as ordinary training data.

**Archived single-scene demonstration — not the current event baseline:**

| Measurement | Actual result |
| --- | ---: |
| IoU | 0.644804 |
| Precision | 0.827280 |
| Recall | 0.745113 |
| F1 / Dice | 0.784050 |
| Valid evaluated pixels | 262045 |

Two independent runs produced identical loss history, evaluation and checkpoint
SHA-256 in this environment. Full run metadata is in
[the recorded training run](docs/sample-training-run.json). These scores do not
establish generalization, sensor transfer or emergency suitability.



## PostgreSQL/PostGIS and Docker

SQLite is the default and needs no service. For PostGIS, Docker Compose provides
a database and the complete web/API image. Prepare the sample/checkpoint first
using the native bootstrap so the mounted `data/` and `artifacts/` exist.

```bash
cp .env.example .env
# Edit .env and replace POSTGRES_PASSWORD with a local password.
# Use letters/numbers here, or URL-encode reserved characters for DATABASE_URL.
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up --build
```

Then use your Mac's local browser as above. Run only one server on port 8000 at a
time. `docker compose down` stops services and preserves the database volume.
Do not use `down -v` unless you intend to delete that database.
The database is not exposed as a public port. Migrations run at single-process
startup. PostGIS stores region polygons with a GiST index; a geographic
intersection query has been validated. The portable catalog API still uses bbox
filtering, not a claimed advanced spatial query engine.

In the managed cloud, Docker builds additionally need the session CA:

```bash
docker build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t terrasense-ai:local .
```

No TLS verification is disabled. See [architecture and decisions](docs/architecture.md).

## Real-data research and NASA

The current eight-scene pilot was downloaded and trained in the cloud. Ghana
and India supply four training chips, Mekong supplies two validation chips, and
Nigeria supplies two held-out test chips. This custom split is event-disjoint,
not the official full-dataset benchmark. The selected checkpoint uses validation
loss; test scores are reported once after selection. See
[actual held-out results](docs/event-training-run.json).

| Held-out scene | IoU | Precision | Recall | F1/Dice |
| --- | ---: | ---: | ---: | ---: |
| Nigeria_1095404 | 0.472728 | 0.486632 | 0.943004 | 0.641976 |
| Nigeria_143329 | 0.071257 | 0.075175 | 0.577602 | 0.133035 |

These modest and uneven scores expose substantial false positives and limited
transfer. They do not establish broad geographic generalization or flood change.

NASA CMR search found two HLS scenes in the tested region/date range. Protected
asset download and real HLS preparation still need Earthdata credentials. HLS
inference remains disabled because optical bands do not match this radar model.
See [HLS workflow](docs/hls.md). No Prithvi weights or comparison run is claimed.

The official source and label STAC collections declare `license: proprietary`.
Keep imagery and weights private and obtain applicable rights before redistributing
them. Only code and research documentation are included in the GitHub branch;
raw imagery, masks, weights, databases and data-derived screenshots are excluded.

## Project map

| Location | Responsibility |
| --- | --- |
| `backend/app/main.py` | HTTP API, validation, lifecycle, compiled website |
| `backend/app/config.py` | Environment-based paths/settings |
| `backend/app/db.py` | Persistent catalog, provenance, model and job tables |
| `backend/app/services/` | Catalog registration, inference, NASA ingestion |
| `backend/migrations/` | Versioned database schema and PostGIS setup |
| `backend/tests/` | API, model, invalid-data, geospatial and HLS tests |
| `ml/geospatial.py` | Alignment, normalization, metrics, previews, area and masks |
| `ml/model.py`, `ml/train.py` | Small U-Net, deterministic training/validation/testing |
| `frontend/src/` | Responsive application, API client and geographic map |
| `scripts/` | Reproducible setup, startup, data commands and smoke test |
| `data/sample-sources.json` | Pinned sample URLs and verified hashes |
| `.github/workflows/ci.yml` | Automated lint, tests, real-sample integration and build |

## Limitations and remaining delivery

The application is a working local/browser-workspace research prototype. The
small held-out pilot has weak and variable performance, and surface water is not
verified flooding. Live authenticated HLS downloads, broader error/generalization
analysis, Prithvi experiments and a permanent public deployment remain unfinished.
A Codespace provides a private running website for your development session.
Keep it private: production authentication and a distributed job system are not
implemented. No paid service is required for local execution.

Code license: existing MIT `LICENSE`. Third-party dataset STAC declares proprietary
terms; the code license does not cover imagery, labels or learned artifacts.
Cite Bonafilia et al. (2020), Sen1Floods11, Cloud to Street.
