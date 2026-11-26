@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\q1.log
echo STAGE refine-all-v3 %date% %time% >> jobs\q1.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3 --variants prompt_refine --palette cs >> jobs\q1.log 2>&1
echo STAGE refine-all-rw %date% %time% >> jobs\q1.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_core --variants prompt_refine --palette cs >> jobs\q1.log 2>&1
echo STAGE refine-analysis %date% %time% >> jobs\q1.log
..\.venv\Scripts\python.exe -u analysis.py --out results\v3 --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --payloads data\v3_payloads --variants prompt_only,prompt_refine --analysis-dir results\refine\analysis_v3_all --no-overlays >> jobs\q1.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\rw_core --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --payloads data\rw_core_payloads --variants prompt_only,prompt_refine --analysis-dir results\refine\analysis_rw_all --no-overlays >> jobs\q1.log 2>&1
echo STAGE gen2048 %date% %time% >> jobs\q1.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_2048 --variants prompt_only --cases 1-24 --palette cs --size 2048x1152 >> jobs\q1.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\v3_2048 --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --payloads data\v3_payloads --variants prompt_only --cases 1-24 --no-overlays >> jobs\q1.log 2>&1
echo Q1_COMPLETE %date% %time% >> jobs\q1.log
echo done > jobs\q1.done
echo EXIT %errorlevel% %date% %time% >> jobs\q1.log

