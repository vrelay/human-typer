#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v xclip >/dev/null 2>&1; then
  echo "Install xclip first: sudo apt install xclip"
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
echo
echo "Setup done. Run:"
echo "  source .venv/bin/activate && python typer.py"
