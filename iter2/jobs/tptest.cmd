@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\tptest.log
..\.venv\Scripts\python.exe -u training_prep.py >> jobs\tptest.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\tptest.log

