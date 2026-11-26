@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\stage4.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\tune_c05 --variants prompt_only --cases 1-24 --palette cs --cn-scales 0.5,1.0 --size 1024x576 >> jobs\stage4.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\tune_c00 --variants prompt_only --cases 1-24 --palette cs --cn-scales 0.0,1.0 --size 1024x576 >> jobs\stage4.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\tune_c05_hr --variants prompt_only --cases 1-24 --palette cs --cn-scales 0.5,1.0 --size 1280x704 >> jobs\stage4.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\tune_c10_hr --variants prompt_only --cases 1-24 --palette cs --cn-scales 1.0,1.0 --size 1280x704 >> jobs\stage4.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\tune_c05 --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --variants prompt_only --no-overlays >> jobs\stage4.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\tune_c00 --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --variants prompt_only --no-overlays >> jobs\stage4.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\tune_c05_hr --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --variants prompt_only --no-overlays >> jobs\stage4.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\tune_c10_hr --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --variants prompt_only --no-overlays >> jobs\stage4.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\stage4.log

