@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\v3smoke.log
cd /d C:\carla_multicam_kit
powershell -NoProfile -Command "if (-not (Get-NetTCPConnection -LocalPort 2000 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath C:\CARLA\CARLA_0.9.16\CarlaUE4.exe -ArgumentList '-quality-level=Epic','-carla-rpc-port=2000','-RenderOffScreen' -WorkingDirectory C:\CARLA\CARLA_0.9.16 }"
powershell -NoProfile -Command "$t = 0; while (-not (Get-NetTCPConnection -LocalPort 2000 -State Listen -ErrorAction SilentlyContinue) -and $t -lt 180) { Start-Sleep 3; $t += 3 }; Start-Sleep 25"
set PYTHONIOENCODING=utf-8
C:\carla_multicam_kit\.venv\Scripts\python.exe -u generate_cases_v3.py --out C:\carla_multicam_kit\output\v3_smoke --cases 3 --seed 21 --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12 >> C:\Users\mrbqble\Desktop\csci408-probe\iter2\jobs\v3smoke.log 2>&1
powershell -NoProfile -Command "Get-Process CarlaUE4* -ErrorAction SilentlyContinue | Stop-Process -Force"
echo EXIT %errorlevel% %date% %time% >> jobs\v3smoke.log

