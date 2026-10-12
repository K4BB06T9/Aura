#!/usr/bin/env bash
# One-click build: creates dist/Aura (Linux) or dist/Aura.app (macOS)
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt pyinstaller
python build.py
echo "Done! Look in the dist/ folder."
