@echo off
chcp 65001 >nul
setlocal
call "%~dp0config.bat"
set PYTHONIOENCODING=utf-8

REM ============================================================
REM  ЗАПУСК СБОРА ДАТАСЕТА. Поменяй параметры ниже и запусти.
REM  Перед этим должен работать сервер (scripts\03_start_carla.bat).
REM ============================================================

REM Количество камер (ракурсов)
set CAMERAS=3
REM Интервал сохранения, секунды симуляции
set INTERVAL=10
REM Сколько снимков сделать
set SNAPSHOTS=50
REM Карта: Town10HD_Opt, Town03_Opt, Town05_Opt ... (пусто = текущая)
set TOWN=Town10HD_Opt
REM Номер перекрёстка на карте (0, 1, 2 ...)
set JUNCTION=0
REM Высота камер (м) и расстояние до центра перекрёстка (м)
set CAM_HEIGHT=8
set RADIUS=25
REM Пресет качества: clean / cctv / hd
set PRESET=cctv
REM Типы камер: rgb,depth,semantic,instance
set SENSORS=rgb,semantic
REM Погода: ClearNoon, CloudyNoon, WetNoon, HardRainNoon, ClearSunset, ClearNight ...
set WEATHER=ClearNoon
REM Количество машин и пешеходов
set VEHICLES=40
set WALKERS=30

REM Папка вывода с датой и временем, чтобы прогоны не перезаписывали друг друга
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%T
set OUT=%KIT_DIR%output\run_%STAMP%

set TOWN_ARG=
if not "%TOWN%"=="" set TOWN_ARG=--town %TOWN%

"%VENV_DIR%\Scripts\python.exe" "%KIT_DIR%carla_multicam.py" ^
    %TOWN_ARG% ^
    --junction-index %JUNCTION% ^
    --cameras %CAMERAS% ^
    --interval %INTERVAL% ^
    --snapshots %SNAPSHOTS% ^
    --cam-height %CAM_HEIGHT% ^
    --radius %RADIUS% ^
    --preset %PRESET% ^
    --sensors %SENSORS% ^
    --weather %WEATHER% ^
    --vehicles %VEHICLES% ^
    --walkers %WALKERS% ^
    --out "%OUT%" ^
    %*

echo.
echo Результат: %OUT%
pause
