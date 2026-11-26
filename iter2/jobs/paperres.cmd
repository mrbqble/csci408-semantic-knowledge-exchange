@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\paperres.log
set PYTHONIOENCODING=utf-8
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_paper --variants k1,prompt_only --palette cs --size 1920x1088 >> jobs\paperres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_paper --variants k1,prompt_only --palette cs --size 1920x1088 >> jobs\paperres.log 2>&1
echo PAPERRES_COMPLETE %date% %time% >> jobs\paperres.log 2>&1
echo done > jobs\paperres.done
echo EXIT %errorlevel% %date% %time% >> jobs\paperres.log

