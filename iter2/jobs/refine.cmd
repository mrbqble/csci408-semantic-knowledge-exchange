@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\refine.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3 --variants prompt_refine --cases 112,106,69,91,88,42,52,59,89,101 --palette cs >> jobs\refine.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_core --variants prompt_refine --cases 25,7,19,1,13,235,241,217,223,277 --palette cs >> jobs\refine.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\v3 --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --payloads data\v3_payloads --variants prompt_only,prompt_refine --cases 112,106,69,91,88,42,52,59,89,101 --analysis-dir results\refine\analysis_v3 --no-overlays >> jobs\refine.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\rw_core --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --payloads data\rw_core_payloads --variants prompt_only,prompt_refine --cases 25,7,19,1,13,235,241,217,223,277 --analysis-dir results\refine\analysis_rw --no-overlays >> jobs\refine.log 2>&1
..\.venv\Scripts\python.exe -u refine_report.py >> jobs\refine.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\refine.log

