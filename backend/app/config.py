"""Environment-based paths and connection settings."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("TERRASENSE_DATA_DIR", ROOT / "data")).resolve()
ARTIFACTS = Path(os.environ.get("TERRASENSE_MODEL_DIR", ROOT / "artifacts/baseline")).resolve()
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA / 'terrasense.db'}")
