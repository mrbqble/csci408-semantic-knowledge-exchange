@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\smokecheck.log
..\.venv\Scripts\python.exe -u payloads.py --dataset C:\carla_multicam_kit\output\v3_smoke --out _scratch\smoke_data --cases 1 >> jobs\smokecheck.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads _scratch\smoke_data --out _scratch\smoke_results --variants k1,prompt_only --cases 1 >> jobs\smokecheck.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out _scratch\smoke_results --dataset C:\carla_multicam_kit\output\v3_smoke --payloads _scratch\smoke_data --variants k1,prompt_only >> jobs\smokecheck.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\smokecheck.log

