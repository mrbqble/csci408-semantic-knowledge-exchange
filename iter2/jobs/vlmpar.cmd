@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\vlmpar.log
set PYTHONIOENCODING=utf-8
echo STAGE core-parallel %date% %time% >> jobs\vlm_par.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --runs core --workers 4 >> jobs\vlm_par.log 2>&1
echo STAGE extra %date% %time% >> jobs\vlm_par.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --runs extra --workers 4 >> jobs\vlm_par.log 2>&1
echo STAGE retry-pass %date% %time% >> jobs\vlm_par.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --runs all --workers 4 >> jobs\vlm_par.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --report > jobs\vlm_report.txt 2>&1
echo VLM_COMPLETE %date% %time% >> jobs\vlm_par.log 2>&1
echo done > jobs\vlm.done
echo EXIT %errorlevel% %date% %time% >> jobs\vlmpar.log

