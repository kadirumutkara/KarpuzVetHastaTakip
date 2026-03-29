@echo off
cd /d %~dp0

if not exist installer-dist\setup.exe (
  echo installer-dist\setup.exe bulunamadi.
  exit /b 1
)

set ZIP_NAME=KarpuzVetPatoloji-Windows.zip
set DESKTOP_DIR=%USERPROFILE%\Desktop

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (Test-Path '%DESKTOP_DIR%\%ZIP_NAME%') { Remove-Item '%DESKTOP_DIR%\%ZIP_NAME%' -Force }; Compress-Archive -Path 'installer-dist\setup.exe' -DestinationPath '%DESKTOP_DIR%\%ZIP_NAME%' -Force"

echo Zip olusturuldu: %DESKTOP_DIR%\%ZIP_NAME%
