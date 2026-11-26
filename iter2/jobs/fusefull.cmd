@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\fusefull.log
set PYTHONIOENCODING=utf-8
echo STAGE rw-support %date% %time% >> jobs\fusefull.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_native --out results\rw_support --variants k1 --k1-cams all --size 896x512 --palette cs >> jobs\fusefull.log 2>&1
echo STAGE rw-fusion %date% %time% >> jobs\fusefull.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_fuse --variants fuse,fuse_noip --size 1920x1088 --palette cs --fuse-main results\rw_paper\k1 --fuse-support results\rw_support\k1 >> jobs\fusefull.log 2>&1
echo STAGE v3-support %date% %time% >> jobs\fusefull.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_native --out results\v3_support --variants k1 --k1-cams all --size 896x512 --palette cs >> jobs\fusefull.log 2>&1
echo STAGE v3-fusion %date% %time% >> jobs\fusefull.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_fuse --variants fuse,fuse_noip --size 1920x1088 --palette cs --fuse-main results\v3_paper\k1 --fuse-support results\v3_support\k1 >> jobs\fusefull.log 2>&1
echo FUSEFULL_COMPLETE %date% %time% >> jobs\fusefull.log 2>&1
echo done > jobs\fusefull.done
echo EXIT %errorlevel% %date% %time% >> jobs\fusefull.log

