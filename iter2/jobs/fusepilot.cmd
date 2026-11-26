@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\fusepilot.log
set PYTHONIOENCODING=utf-8
echo STAGE support-reconstructions %date% %time% >> jobs\fusepilot.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_native --out results\rw_support --variants k1 --k1-cams all --size 896x512 --palette cs --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115 >> jobs\fusepilot.log 2>&1
echo STAGE fusion %date% %time% >> jobs\fusepilot.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_fuse --variants fuse,fuse_noip --size 1920x1088 --palette cs --fuse-main results\rw_paper\k1 --fuse-support results\rw_support\k1 --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115 >> jobs\fusepilot.log 2>&1
echo STAGE judge %date% %time% >> jobs\fusepilot.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --runs rw_fuse,rw_fuse_noip --workers 4 >> jobs\fusepilot.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --runs rw_fuse,rw_fuse_noip --workers 4 >> jobs\fusepilot.log 2>&1
..\.venv\Scripts\python.exe -u vlm_judge.py --report > jobs\vlm_report.txt 2>&1
echo FUSEPILOT_COMPLETE %date% %time% >> jobs\fusepilot.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\fusepilot.log

