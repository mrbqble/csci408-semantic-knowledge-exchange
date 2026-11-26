@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\v3test.log
set V3S=C:\carla_multicam_kit\output\v3_smoke
..\.venv\Scripts\python.exe -u payloads.py --dataset %V3S% --out data\v3_smoke_payloads >> jobs\v3test.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_smoke_payloads --out results\v3_smoke --variants k1,prompt_only --cases 1-3 --palette cs >> jobs\v3test.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\v3_smoke --dataset %V3S% --payloads data\v3_smoke_payloads --variants k1,prompt_only >> jobs\v3test.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\v3test.log

