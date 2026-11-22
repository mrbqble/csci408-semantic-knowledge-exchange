@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\hr2048test.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_2048 --variants prompt_only --cases 1 --palette cs --size 2048x1152 >> jobs\hr2048test.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\hr2048test.log

