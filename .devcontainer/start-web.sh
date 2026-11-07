#!/usr/bin/env bash
# Codespaces forwards this server to an authenticated HTTPS browser address.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python - <<'PY'
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

url = 'http://127.0.0.1:8000/openapi.json'
def ready():
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.load(response)['info']['title'] == 'Avenry Earth Intelligence'
    except (OSError, ValueError, KeyError):
        return False

if ready():
    print('Avenry Earth Intelligence is already running. Open port 8000 in the Ports tab.')
else:
    logfile = Path('/tmp/avenry-web.log')
    with logfile.open('ab') as log:
        process = subprocess.Popen(
            ['.venv/bin/python', '-m', 'uvicorn', 'backend.app.main:app',
             '--host', '0.0.0.0', '--port', '8000'],
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    for _ in range(120):
        if process.poll() is not None:
            raise SystemExit(f'Website startup failed. Read {logfile}.')
        if ready():
            print('Avenry Earth Intelligence is ready. Open port 8000 in the Ports tab.')
            break
        time.sleep(.5)
    else:
        raise SystemExit(f'Website readiness timed out. Read {logfile}.')
PY
