@echo off
cd /d %~dp0
set PYINSTALLER_CONFIG_DIR=%cd%\.pyinstaller
py -3 -m PyInstaller --noconfirm KarpuzVetPatoloji.spec
