import json

import pytest

from scripts.deploy_huggingface import prepare


def test_space_package_contains_code_and_bootstrap_but_no_data(tmp_path):
    output = tmp_path / "space"
    assert prepare(output) > 15
    assert (output / "frontend/package-lock.json").is_file()
    assert (output / "backend/app/main.py").is_file()
    assert (output / "scripts/serve_container.py").is_file()
    assert "app_port: 7860" in (output / "README.md").read_text()
    docker = (output / "Dockerfile").read_text()
    assert "AVENRY_BOOTSTRAP_DATA=1" in docker
    assert "EXPOSE 7860" in docker
    assert "scripts.serve_container" in docker
    assert not list(output.rglob("*.tif"))
    assert not list(output.rglob("*.pt"))
    assert not (output / ".env").exists()
    json.loads((output / "frontend/package.json").read_text())


def test_deployment_does_not_overwrite_existing_files(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "work.txt").write_text("keep")
    with pytest.raises(ValueError, match="empty"):
        prepare(target)
    assert (target / "work.txt").read_text() == "keep"
