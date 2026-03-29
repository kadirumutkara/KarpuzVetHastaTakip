#!/bin/bash
set -e
cd "$(dirname "$0")"
export PYINSTALLER_CONFIG_DIR="$(pwd)/.pyinstaller"
/usr/bin/python3 -m PyInstaller --noconfirm --windowed --name KarpuzVetPatoloji --add-data "web:web" app.py
