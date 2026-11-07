"""Create a personal local-run bundle without environments, credentials or Git metadata."""

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT.parent / "terrasense-ai.zip")
    args = parser.parse_args()
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if not path.is_file() or path.is_symlink() or set(relative.parts) & EXCLUDE:
                continue
            if path.name.startswith(".env") and path.name != ".env.example":
                continue
            if (
                path.suffix in {".db", ".log", ".part"}
                or ".db-" in path.name
                or path.resolve() == args.output.resolve()
            ):
                continue
            if relative.parts[:2] == ("data", "results"):
                continue
            archive.write(path, Path("terrasense-ai") / relative)
    print(f"Created {args.output} ({args.output.stat().st_size} bytes)")
    print(
        "Personal research bundle includes third-party sample data and weights; verify source terms before public redistribution."
    )


if __name__ == "__main__":
    main()
