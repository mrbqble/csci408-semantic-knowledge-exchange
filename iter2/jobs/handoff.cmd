@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\handoff.log
set PYTHONIOENCODING=utf-8&& set PYTHONPATH=C:\Users\mrbqble\Desktop\csci408-probe\iter2&& ..\.venv\Scripts\python.exe -u make_handoff.py "C:\Users\mrbqble\Desktop\CSCI408_report_handoff_2026-11-22" >> jobs\handoff.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\handoff.log

