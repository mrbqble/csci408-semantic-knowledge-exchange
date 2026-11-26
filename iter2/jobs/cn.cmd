@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\cn.log
set PYTHONIOENCODING=utf-8
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_cn07_15 --variants prompt_only --palette cs --cn-scales 0.7,1.5 >> jobs\cn.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_cn07_15 --variants prompt_only --palette cs --cn-scales 0.7,1.5 >> jobs\cn.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\v3_cn07_15 --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --payloads data\v3_payloads --variants prompt_only --no-overlays >> jobs\cn.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\rw_cn07_15 --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --payloads data\rw_core_payloads --variants prompt_only --no-overlays >> jobs\cn.log 2>&1
..\.venv\Scripts\python.exe -u gt_eval.py --cases 1-112 --out results\gt_eval_cn07_15.json default=results/v3/analysis/prompt_only cn0.7_seg1.5=results/v3_cn07_15/analysis/prompt_only > jobs\gt_eval_cn07_15.txt 2>&1
echo CN_COMPLETE %date% %time% >> jobs\cn.log
echo done > jobs\cn.done
echo EXIT %errorlevel% %date% %time% >> jobs\cn.log

