@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\tunesel.log
set PYTHONIOENCODING=utf-8
:wait
findstr /c:"VLM_TUNE_COMPLETE" jobs\vlm_tune.log > nul && goto go
timeout /t 300 /nobreak > nul
goto wait
:go
..\.venv\Scripts\python.exe -u tune_select.py >> jobs\tunesel.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --report > jobs\vlm_report.txt 2>&1
echo TUNESEL_COMPLETE %date% %time% >> jobs\tunesel.log
echo EXIT %errorlevel% %date% %time% >> jobs\tunesel.log

