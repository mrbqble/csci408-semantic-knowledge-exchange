@echo off
chcp 65001 >nul
setlocal
call "%~dp0config.bat"
set PYTHONIOENCODING=utf-8

REM ============================================================
REM  Сбор с камерами, заданными вручную в JSON-файле
REM  (у каждой камеры своя высота, наклон, FOV, разрешение).
REM  Пример конфига: configs\cameras_example.json
REM  Можно перетащить свой .json файл прямо на этот .bat
REM ============================================================

set "CAM_CONFIG=%~1"
if "%CAM_CONFIG%"=="" set "CAM_CONFIG=%KIT_DIR%configs\cameras_example.json"

for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%T
set "OUT=%KIT_DIR%output\config_%STAMP%"

echo Конфиг камер: %CAM_CONFIG%
"%VENV_DIR%\Scripts\python.exe" "%KIT_DIR%carla_multicam.py" ^
    --town Town10HD_Opt ^
    --camera-config "%CAM_CONFIG%" ^
    --interval 10 ^
    --snapshots 50 ^
    --preset cctv ^
    --sensors rgb,semantic,instance ^
    --out "%OUT%"

echo.
echo Результат: %OUT%
pause
