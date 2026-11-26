@echo off
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\config.bat"

echo ============================================================
echo  Шаг 1. Скачивание CARLA %CARLA_VERSION% в %CARLA_ROOT%
echo ============================================================
echo.
set /p MAPS="Скачать дополнительные карты? (+ несколько ГБ) [y/N]: "

for %%I in ("%CARLA_ROOT%\..") do set "INSTALL_ROOT=%%~fI"

set "PS_ARGS=-Version %CARLA_VERSION% -InstallRoot "%INSTALL_ROOT%""
if /i "%MAPS%"=="y" set "PS_ARGS=%PS_ARGS% -WithAdditionalMaps"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%01_download_carla.ps1" %PS_ARGS%
pause
