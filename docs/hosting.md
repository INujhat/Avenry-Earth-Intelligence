# Hugging Face deployment for NujAMred

Status: source package prepared; 15 tests pass; local port-7860 startup and real
inference checked. No Space has been created and no hosted website validated yet.

## Secure access required

The environment had no HF token or logged-in Hugging Face connector. A requirement
named `HF_TOKEN` is saved in the environment settings, sent only to `huggingface.co`.
Add a write-capable token securely there, never to chat, Git, logs or this file.
Network additions for the Hub and expected Space hostname are in the same draft.
A draft save alone does not apply network changes or deploy an application.

## Operator commands (after access is configured)

```bash
.venv/bin/python -m pip install -r requirements-deploy.txt
.venv/bin/python -m scripts.deploy_huggingface --username NujAMred
```

The script verifies the token's account name before making changes and creates
only a free `cpu-basic` Docker Space. It uploads a source-only package; imagery,
weights, local databases and credentials are excluded. It refuses to overwrite
an existing Space. If upload fails after creation, inspect the newly created
Space before retrying; do not repeatedly create repositories.

The initial Space is **private** so the owner can inspect the working product.
The dataset's official STAC declares proprietary terms; obtain applicable rights
before redistributing imagery, labels or learned artifacts publicly. This is not
an emergency warning service or a validated flood-change detector.

The Space listens on port 7860, serves the React website and API together, and
prepares the bounded real dataset and CPU model on first startup. Its initial
build/start may take several minutes. Free hosting can sleep and ephemeral data
or analysis history can disappear on rebuild/restart. No paid hardware or storage
is requested. Model predictions and metrics remain research outputs.

After upload, inspect the Hub build/runtime status and actual returned host URL.
Verify health, catalog, a completed analysis, map assets and a GeoTIFF download
before calling the hosted website ready. Do not provide an anticipated hostname
as a working website link before these checks pass.
