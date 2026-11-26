@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\vlm.log
set PYTHONIOENCODING=utf-8
:waitprep
if exist jobs\vlmprep.done goto key
timeout /t 60 /nobreak > nul
goto waitprep
:key
..\.venv\Scripts\python.exe -u vlm_judge.py --runs core >> jobs\vlm.log 2>&1
if errorlevel 1 (
  timeout /t 600 /nobreak > nul
  goto key
)
..\.venv\Scripts\python.exe -u vlm_judge.py --runs extra >> jobs\vlm.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --runs all >> jobs\vlm.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --report > jobs\vlm_report.txt 2>&1
echo VLM_COMPLETE %date% %time% >> jobs\vlm.log
echo done > jobs\vlm.done
echo EXIT %errorlevel% %date% %time% >> jobs\vlm.log

