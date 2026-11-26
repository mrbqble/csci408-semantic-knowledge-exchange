@echo off
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\config.bat"
set PYTHONIOENCODING=utf-8

echo Шаг 4. Проверка связи с сервером CARLA
"%VENV_DIR%\Scripts\python.exe" "%KIT_DIR%check_connection.py"
pause
