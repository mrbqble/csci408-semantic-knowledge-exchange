@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\fusiondemo.log
set PYTHONIOENCODING=utf-8
..\.venv\Scripts\python.exe -u fusion_demo.py --dataset rw --case 1 >> jobs\fusiondemo.log 2>&1
..\.venv\Scripts\python.exe -u fusion_demo.py --dataset v3 --case 10 >> jobs\fusiondemo.log 2>&1
echo FUSIONDEMO_COMPLETE %date% %time% >> jobs\fusiondemo.log
powershell -NoProfile -Command "Start-ScheduledTask -TaskName csci408_fusepilot"
echo EXIT %errorlevel% %date% %time% >> jobs\fusiondemo.log

