@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\vlm2.log
set PYTHONIOENCODING=utf-8
echo STAGE existing-setups %date% %time% >> jobs\vlm.log
..\.venv\Scripts\python.exe -u vlm_judge.py --runs v3_default,v3_k1,rw_default,rw_k1 >> jobs\vlm.log 2>&1
:waitprep
if exist jobs\vlmprep.done goto core
timeout /t 60 /nobreak > nul
goto waitprep
:core
echo STAGE core %date% %time% >> jobs\vlm.log
..\.venv\Scripts\python.exe -u vlm_judge.py --runs core >> jobs\vlm.log 2>&1
echo STAGE extra %date% %time% >> jobs\vlm.log
..\.venv\Scripts\python.exe -u vlm_judge.py --runs extra >> jobs\vlm.log 2>&1
echo STAGE retry-pass %date% %time% >> jobs\vlm.log
..\.venv\Scripts\python.exe -u vlm_judge.py --runs all >> jobs\vlm.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --report > jobs\vlm_report.txt 2>&1
echo VLM_COMPLETE %date% %time% >> jobs\vlm.log
echo done > jobs\vlm.done
echo EXIT %errorlevel% %date% %time% >> jobs\vlm2.log

