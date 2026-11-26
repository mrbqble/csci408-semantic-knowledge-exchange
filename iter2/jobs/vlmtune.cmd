@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\vlmtune.log
set PYTHONIOENCODING=utf-8
:loop
..\.venv\Scripts\python.exe -u vlm_judge.py --runs fullres_tune --workers 4 >> jobs\vlm_tune.log 2>&1
if exist jobs\fullres.done goto final
timeout /t 600 /nobreak > nul
goto loop
:final
..\.venv\Scripts\python.exe -u vlm_judge.py --runs fullres_tune --workers 4 >> jobs\vlm_tune.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --runs fullres_tune --workers 4 >> jobs\vlm_tune.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --report > jobs\vlm_report.txt 2>&1
echo VLM_TUNE_COMPLETE %date% %time% >> jobs\vlm_tune.log
echo EXIT %errorlevel% %date% %time% >> jobs\vlmtune.log

