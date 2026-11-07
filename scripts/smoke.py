"""Exercise a running application, including a real background analysis and export."""

import argparse
import time

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.url, timeout=15, trust_env=False) as client:
        # This is only a local loopback test; never use it to access remote services.
        from urllib.parse import urlparse

        if urlparse(args.url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            parser.error("Smoke checks are restricted to local loopback URLs")
        client.get("/health").raise_for_status()
        response = client.get("/api/v1/scenes")
        response.raise_for_status()
        scene = response.json()["items"][0]
        response = client.post("/api/v1/analyses", json={"scene_id": scene["id"]})
        response.raise_for_status()
        job = response.json()
        for _ in range(120):
            response = client.get("/api/v1/analyses/" + job["id"])
            response.raise_for_status()
            status = response.json()["status"]
            if status in {"completed", "failed"}:
                break
            time.sleep(0.25)
        if status != "completed":
            raise RuntimeError(f"Analysis did not complete: {status}")
        result = client.get("/api/v1/analyses/" + job["id"] + "/results")
        result.raise_for_status()
        metadata = result.json()
        export = client.get(metadata["downloads"]["geotiff"])
        export.raise_for_status()
        assert export.headers["content-type"] == "image/tiff"
        assert export.content[:4] in {b"II*\x00", b"MM\x00*"}
        print(
            f"PASS health/catalog/job/results/GeoTIFF: {job['id']}; area={metadata['detected_water_km2']:.6f} km²; scope={metadata['evaluation_scope']}"
        )


if __name__ == "__main__":
    main()
