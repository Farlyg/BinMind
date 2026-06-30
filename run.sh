#!/usr/bin/env bash
set -e
python3 -m pip install -r requirements.txt >/dev/null 2>&1 || true
python3 main.py "$@"
