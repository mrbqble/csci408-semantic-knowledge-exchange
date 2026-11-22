@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\stage1.log
..\.venv\Scripts\python.exe -u payloads.py --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --out data\carla_v2_payloads >> jobs\stage1.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\pilot_cs --variants k1 --cases 1-24 --palette cs >> jobs\stage1.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\pilot_ade --variants k1 --cases 1-24 --palette ade >> jobs\stage1.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\pilot_cs --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --payloads data\carla_v2_payloads --variants k1 >> jobs\stage1.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\pilot_ade --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --payloads data\carla_v2_payloads --variants k1 >> jobs\stage1.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\stage1.log

