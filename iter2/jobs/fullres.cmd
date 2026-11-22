@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\fullres.log
set PYTHONIOENCODING=utf-8
echo STAGE rw-supports-fullres %date% %time% >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_paper --variants k1 --k1-cams all --size 1920x1088 --palette cs >> jobs\fullres.log 2>&1
echo STAGE rw-fusion-fullres %date% %time% >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_fuseF_st0.5 --variants fuse --size 1920x1088 --palette cs --fuse-main results\rw_paper\k1 --fuse-support results\rw_paper\k1 >> jobs\fullres.log 2>&1
echo STAGE v3-supports-fullres %date% %time% >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_paper --variants k1 --k1-cams all --size 1920x1088 --palette cs >> jobs\fullres.log 2>&1
echo STAGE v3-fusion-fullres %date% %time% >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_fuseF_st0.5 --variants fuse --size 1920x1088 --palette cs --fuse-main results\v3_paper\k1 --fuse-support results\v3_paper\k1 >> jobs\fullres.log 2>&1
echo STAGE tuning %date% %time% >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_fuseF_st0.3 --variants fuse --fuse-strength 0.3 --size 1920x1088 --palette cs --fuse-main results\v3_paper\k1 --fuse-support results\v3_paper\k1 --cases 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56 >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_fuseF_st0.4 --variants fuse --fuse-strength 0.4 --size 1920x1088 --palette cs --fuse-main results\v3_paper\k1 --fuse-support results\v3_paper\k1 --cases 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56 >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_fuseF_st0.6 --variants fuse --fuse-strength 0.6 --size 1920x1088 --palette cs --fuse-main results\v3_paper\k1 --fuse-support results\v3_paper\k1 --cases 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56 >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_fuseF_st0.5 --variants fuse@0.5,fuse@0.75 --size 1920x1088 --palette cs --fuse-main results\v3_paper\k1 --fuse-support results\v3_paper\k1 --cases 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56 >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_fuseF_st0.3 --variants fuse --fuse-strength 0.3 --size 1920x1088 --palette cs --fuse-main results\rw_paper\k1 --fuse-support results\rw_paper\k1 --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175 >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_fuseF_st0.4 --variants fuse --fuse-strength 0.4 --size 1920x1088 --palette cs --fuse-main results\rw_paper\k1 --fuse-support results\rw_paper\k1 --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175 >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_fuseF_st0.6 --variants fuse --fuse-strength 0.6 --size 1920x1088 --palette cs --fuse-main results\rw_paper\k1 --fuse-support results\rw_paper\k1 --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175 >> jobs\fullres.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_fuseF_st0.5 --variants fuse@0.5,fuse@0.75 --size 1920x1088 --palette cs --fuse-main results\rw_paper\k1 --fuse-support results\rw_paper\k1 --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175 >> jobs\fullres.log 2>&1
echo FULLRES_COMPLETE %date% %time% >> jobs\fullres.log 2>&1
echo done > jobs\fullres.done
echo EXIT %errorlevel% %date% %time% >> jobs\fullres.log

