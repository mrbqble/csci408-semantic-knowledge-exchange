@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\refinesmoke.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3 --variants prompt_refine --cases 112 --palette cs >> jobs\refinesmoke.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\refinesmoke.log

