# ============================================================
#  Шаг 1. Скачивание и распаковка CARLA 0.9.16 (готовая сборка, без Unreal Engine)
#  Запуск: правый клик -> "Выполнить с помощью PowerShell"
#  или из 01_download_carla.bat
# ============================================================

param(
    [string]$Version = "0.9.16",
    [string]$InstallRoot = "C:\CARLA",
    [switch]$WithAdditionalMaps
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # иначе Invoke-WebRequest качает в десятки раз медленнее

$carlaDir = Join-Path $InstallRoot "CARLA_$Version"
$zipUrl   = "https://downloads.carlasim.com/Windows/CARLA_$Version.zip"
$mapsUrl  = "https://downloads.carlasim.com/Windows/AdditionalMaps_$Version.zip"
$zipPath  = Join-Path $InstallRoot "CARLA_$Version.zip"
$mapsPath = Join-Path $InstallRoot "AdditionalMaps_$Version.zip"

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

function Download($url, $dest) {
    if (Test-Path $dest) {
        Write-Host "Уже скачано: $dest" -ForegroundColor Yellow
        return
    }
    Write-Host "Скачиваю $url"
    Write-Host "Это большой файл (несколько ГБ), может занять долго..." -ForegroundColor Cyan
    # curl.exe встроен в Windows 10/11, умеет докачку (-C -) и показывает прогресс
    & curl.exe -L -C - --retry 5 -o "$dest.part" $url
    if ($LASTEXITCODE -ne 0) { throw "Ошибка скачивания $url" }
    Move-Item "$dest.part" $dest -Force
}

function Extract($zip, $dest) {
    Write-Host "Распаковываю $zip -> $dest"
    $sevenZip = "C:\Program Files\7-Zip\7z.exe"
    if (Test-Path $sevenZip) {
        & $sevenZip x $zip "-o$dest" -y | Out-Null
    } else {
        # tar.exe встроен в Windows 10+, распаковывает zip быстрее, чем Expand-Archive
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        & tar.exe -xf $zip -C $dest
        if ($LASTEXITCODE -ne 0) { Expand-Archive -Path $zip -DestinationPath $dest -Force }
    }
}

# 1. Основной пакет
if (Test-Path (Join-Path $carlaDir "CarlaUE4.exe")) {
    Write-Host "CARLA уже установлена в $carlaDir" -ForegroundColor Green
} else {
    Download $zipUrl $zipPath
    Extract $zipPath $carlaDir
    # Некоторые архивы содержат вложенную папку - поднимаем содержимое на уровень выше
    $exe = Get-ChildItem -Path $carlaDir -Filter "CarlaUE4.exe" -Recurse -Depth 2 | Select-Object -First 1
    if (-not $exe) { throw "CarlaUE4.exe не найден после распаковки" }
    if ($exe.DirectoryName -ne $carlaDir) {
        Get-ChildItem $exe.DirectoryName | Move-Item -Destination $carlaDir -Force
    }
}

# 2. Дополнительные карты (Town06, Town07, Town10HD полная и т.д.) - по желанию
if ($WithAdditionalMaps) {
    Download $mapsUrl $mapsPath
    Write-Host "Распаковываю дополнительные карты прямо в папку CARLA"
    Extract $mapsPath $carlaDir
}

Write-Host ""
Write-Host "Готово. CARLA установлена в: $carlaDir" -ForegroundColor Green
Write-Host "ZIP-архивы можно удалить, чтобы освободить место: $InstallRoot\*.zip"
