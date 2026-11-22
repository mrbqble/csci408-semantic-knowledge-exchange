@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\config.bat"

echo ============================================================
echo  Шаг 2. Python-окружение для CARLA %CARLA_VERSION%
echo ============================================================

REM --- 1. Проверяем Python нужной версии через лаунчер py
py -%PY_VERSION% --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python %PY_VERSION% не найден.
    echo Установи его с https://www.python.org/downloads/ ^(Windows installer 64-bit^)
    echo и при установке отметь "Add python.exe to PATH" и "py launcher".
    echo Либо поменяй PY_VERSION в config.bat на 3.10 или 3.11, если они установлены.
    pause & exit /b 1
)
py -%PY_VERSION% --version

REM --- 2. Виртуальное окружение
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Создаю виртуальное окружение в %VENV_DIR%
    py -%PY_VERSION% -m venv "%VENV_DIR%"
    if errorlevel 1 ( echo [ОШИБКА] не удалось создать venv & pause & exit /b 1 )
)
set "PY=%VENV_DIR%\Scripts\python.exe"

"%PY%" -m pip install --upgrade pip

REM --- 3. Зависимости проекта
"%PY%" -m pip install -r "%KIT_DIR%requirements.txt"
if errorlevel 1 ( echo [ОШИБКА] установка зависимостей & pause & exit /b 1 )

REM --- 4. CARLA client: сначала с PyPI, если не вышло - из папки CARLA
"%PY%" -m pip install carla==%CARLA_VERSION%
if errorlevel 1 (
    echo Не удалось поставить carla с PyPI, ищу wheel в %CARLA_ROOT%\PythonAPI\carla\dist
    set "WHEEL="
    set "PYTAG=cp%PY_VERSION:.=%"
    for %%W in ("%CARLA_ROOT%\PythonAPI\carla\dist\carla-*-!PYTAG!-*win_amd64.whl") do set "WHEEL=%%~fW"
    if not defined WHEEL (
        echo [ОШИБКА] wheel для !PYTAG! не найден. Посмотри, какие версии Python есть в папке dist,
        echo и поставь такую же в PY_VERSION в config.bat.
        dir /b "%CARLA_ROOT%\PythonAPI\carla\dist"
        pause & exit /b 1
    )
    "%PY%" -m pip install "!WHEEL!"
)

echo.
echo --- Проверка импорта
"%PY%" -c "import carla, numpy, PIL; print('carla OK:', carla.__file__)"
if errorlevel 1 ( echo [ОШИБКА] импорт не прошёл & pause & exit /b 1 )

echo.
echo Готово. Окружение: %VENV_DIR%
pause
