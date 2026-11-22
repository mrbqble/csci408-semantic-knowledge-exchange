@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\vlmcs.log
set PYTHONIOENCODING=utf-8&& ..\.venv\Scripts\python.exe -u vlm_judge.py --runs paper --workers 2 >> jobs\vlm_cs.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\vlmcs.log

