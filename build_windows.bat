@echo off
cd /d %~dp0
set PYINSTALLER_CONFIG_DIR=%cd%\.pyinstaller
python -m PyInstaller --noconfirm KarpuzVetPatoloji.spec
