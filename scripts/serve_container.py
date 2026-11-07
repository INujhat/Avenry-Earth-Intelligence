"""Start local Docker or a CPU-only Hugging Face Space on its configured port."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    os.chdir(ROOT)
    if os.environ.get("AVENRY_BOOTSTRAP_DATA") == "1":
        if not (ROOT / "data/manifest.json").is_file():
            subprocess.run([sys.executable, "-m", "scripts.prepare_subset"], check=True)
            shutil.copyfile(ROOT / "data/subset-manifest.json", ROOT / "data/manifest.json")
        if not all((ROOT / "artifacts/baseline" / name).is_file() for name in ["model.pt", "model.json"]):
            subprocess.run([sys.executable, "-m", "ml.train", "--epochs", "35"], check=True)
    os.execv(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", str(port)],
    )


if __name__ == "__main__":
    main()
