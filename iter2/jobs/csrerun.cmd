@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\csrerun.log
set PYTHONIOENCODING=utf-8
..\.venv\Scripts\python.exe -u payloads.py --dataset data\cs_cases --out data\cs_payloads --seg-input 1024x2048 >> jobs\csrerun.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\cs_payloads --out results\cs_paper --variants k1 --palette cs --size 2048x1024 >> jobs\csrerun.log 2>&1
echo CSRERUN_COMPLETE %date% %time% >> jobs\csrerun.log 2>&1
echo done > jobs\csrerun.done
echo EXIT %errorlevel% %date% %time% >> jobs\csrerun.log

