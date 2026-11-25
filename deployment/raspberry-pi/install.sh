#!/usr/bin/env bash
set -euo pipefail
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential gpsd gpsd-clients
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e ".[gps,dev]"
echo "Install the RGB matrix driver/binding separately for your exact Pi OS and panel."
echo "Copy .env.example to .env and set FLIGHTAWARE_API_KEY before selecting live mode."
