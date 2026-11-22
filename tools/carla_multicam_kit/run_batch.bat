@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
call "%~dp0config.bat"
set PYTHONIOENCODING=utf-8

REM ============================================================
REM  Пакетный сбор: несколько перекрёстков x несколько погод.
REM  Каждая комбинация пишется в свою папку output\batch_...\
REM  Удобно запустить на ночь.
REM ============================================================

set CAMERAS=4
set INTERVAL=10
set SNAPSHOTS=30
set TOWN=Town10HD_Opt
set PRESET=cctv
set SENSORS=rgb,semantic

set JUNCTIONS=0 1 2 3
set WEATHERS=ClearNoon CloudyNoon WetNoon HardRainNoon ClearSunset ClearNight

for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%T
set "BASE=%KIT_DIR%output\batch_%STAMP%"

for %%J in (%JUNCTIONS%) do (
    for %%W in (%WEATHERS%) do (
        echo.
        echo ===== Перекрёсток %%J, погода %%W =====
        "%VENV_DIR%\Scripts\python.exe" "%KIT_DIR%carla_multicam.py" ^
            --town %TOWN% --junction-index %%J --weather %%W ^
            --cameras %CAMERAS% --interval %INTERVAL% --snapshots %SNAPSHOTS% ^
            --preset %PRESET% --sensors %SENSORS% ^
            --out "!BASE!\j%%J_%%W"
        if errorlevel 1 echo [ВНИМАНИЕ] прогон j%%J_%%W завершился с ошибкой, продолжаю
    )
)

echo.
echo Всё готово: %BASE%
pause
