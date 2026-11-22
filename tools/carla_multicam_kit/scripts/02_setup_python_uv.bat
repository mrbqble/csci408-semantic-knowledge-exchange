@echo off
chcp 65001 >nul
setlocal
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\config.bat"
REM Alternative to 02_setup_python.bat for machines that have no Python 3.10-3.12 (uses uv, no admin rights, no system-wide install).
REM Needed because the carla client wheels for Windows exist only for Python 3.10, 3.11 and 3.12.
set "UV=uv"
where uv >nul 2>&1
if errorlevel 1 set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    "%UV%" python install %PY_VERSION%
    "%UV%" venv --python %PY_VERSION% "%VENV_DIR%"
)
"%UV%" pip install --python "%VENV_DIR%\Scripts\python.exe" -r "%KIT_DIR%requirements.txt" carla==%CARLA_VERSION%
"%VENV_DIR%\Scripts\python.exe" "%KIT_DIR%scripts\check_import.py"
pause
