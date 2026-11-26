@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\q3.log
:wait
if exist jobs\q2.done goto go
timeout /t 60 /nobreak > nul
goto wait
:go
set PYTHONIOENCODING=utf-8
..\.venv\Scripts\python.exe -u make_next_report.py >> jobs\q3.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\q3.log

