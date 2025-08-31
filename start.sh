#!/bin/bash
set -e
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m flask run --host=0.0.0.0 --port=3000