@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\apitest.log
set CUDA_VISIBLE_DEVICES=&& set PYTHONPATH=C:\Users\mrbqble\Desktop\csci408-probe\iter2&& ..\.venv\Scripts\python.exe -u _scratch\test_instance_api.py >> jobs\apitest.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\apitest.log

