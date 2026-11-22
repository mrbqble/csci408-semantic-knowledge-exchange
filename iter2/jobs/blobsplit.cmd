@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\blobsplit.log
..\.venv\Scripts\python.exe -u blob_split.py >> jobs\blobsplit.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\blobsplit.log

