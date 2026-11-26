@echo off
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\config.bat"

REM ============================================================
REM  Шаг 3. Запуск сервера CARLA
REM  Использование:
REM    03_start_carla.bat                -> Epic, с окном
REM    03_start_carla.bat Low            -> Low качество (слабая видеокарта)
REM    03_start_carla.bat Epic offscreen -> без окна (быстрее, меньше нагрузка)
REM ============================================================

set "QUALITY=%~1"
if "%QUALITY%"=="" set "QUALITY=Epic"

set "EXTRA="
if /i "%~2"=="offscreen" set "EXTRA=-RenderOffScreen"

if not exist "%CARLA_ROOT%\CarlaUE4.exe" (
    echo [ОШИБКА] Не найден %CARLA_ROOT%\CarlaUE4.exe
    echo Сначала запусти 01_download_carla.bat или поправь CARLA_ROOT в config.bat
    pause & exit /b 1
)

echo Запускаю CARLA: качество=%QUALITY% %EXTRA%
echo Порт: 2000. Первый запуск может грузиться 1-3 минуты (компиляция шейдеров).
echo Окно сервера не закрывай, пока идёт сбор данных.
start "CARLA Server" "%CARLA_ROOT%\CarlaUE4.exe" -quality-level=%QUALITY% -carla-rpc-port=2000 -windowed -ResX=1280 -ResY=720 %EXTRA%
