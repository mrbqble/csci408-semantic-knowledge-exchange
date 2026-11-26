@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\vlmprep.log
set PYTHONIOENCODING=utf-8
echo STAGE payloads-native %date% %time% >> jobs\vlmprep.log
..\.venv\Scripts\python.exe -u payloads.py --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --out data\v3_native --work-size 896x512 >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u payloads.py --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --out data\rw_native --work-size 896x512 --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175,181,187,193,199,205,211,217,223,229,235,241,247,253,259,265,271,277,283,289,295,301,307,313,319,325,331,337,343,349,355,361 >> jobs\vlmprep.log 2>&1
echo STAGE generate %date% %time% >> jobs\vlmprep.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_native --out results\v3_native_ade --variants k1,prompt_only --size 896x512 --palette ade >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_native --out results\rw_native_ade --variants k1,prompt_only --size 896x512 --palette ade >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_native --out results\v3_native_cs --variants prompt_only --size 896x512 --palette cs >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_native --out results\rw_native_cs --variants prompt_only --size 896x512 --palette cs >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_payloads --out results\v3_ade --variants prompt_only --palette ade >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_core_payloads --out results\rw_ade --variants prompt_only --palette ade >> jobs\vlmprep.log 2>&1
echo STAGE analysis %date% %time% >> jobs\vlmprep.log
..\.venv\Scripts\python.exe -u analysis.py --out results\v3_native_ade --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --variants k1,prompt_only --no-overlays >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\rw_native_ade --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --variants k1,prompt_only --no-overlays >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\v3_native_cs --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --variants prompt_only --no-overlays >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\rw_native_cs --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --variants prompt_only --no-overlays >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\v3_ade --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --variants prompt_only --no-overlays >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\rw_ade --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --variants prompt_only --no-overlays >> jobs\vlmprep.log 2>&1
..\.venv\Scripts\python.exe -u gt_eval.py --cases 1-112 --out results\gt_eval_points.json default=results/v3/analysis/prompt_only both_fixes=results/v3_native_ade/analysis/prompt_only resolution_only=results/v3_native_cs/analysis/prompt_only palette_only=results/v3_ade/analysis/prompt_only cn0.7_seg1.5=results/v3_cn07_15/analysis/prompt_only k1_default=results/v3/analysis/k1 k1_both_fixes=results/v3_native_ade/analysis/k1 > jobs\gt_eval_points.txt 2>&1
echo VLMPREP_COMPLETE %date% %time% >> jobs\vlmprep.log
echo done > jobs\vlmprep.done
echo EXIT %errorlevel% %date% %time% >> jobs\vlmprep.log

