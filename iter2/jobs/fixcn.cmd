@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\fixcn.log
set PYTHONIOENCODING=utf-8
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\v3_native --out results\v3_native_ade_cn --variants k1,prompt_only --size 896x512 --palette ade --cn-scales 0.7,1.5 >> jobs\fixcn.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\rw_native --out results\rw_native_ade_cn --variants k1,prompt_only --size 896x512 --palette ade --cn-scales 0.7,1.5 >> jobs\fixcn.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\v3_native_ade_cn --dataset C:\carla_multicam_kit\output\carla_dataset_v3_ids --variants k1,prompt_only --no-overlays >> jobs\fixcn.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\rw_native_ade_cn --dataset 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175,181,187,193,199,205,211,217,223,229,235,241,247,253,259,265,271,277,283,289,295,301,307,313,319,325,331,337,343,349,355,361 --variants k1,prompt_only --no-overlays >> jobs\fixcn.log 2>&1
..\.venv\Scripts\python.exe -u gt_eval.py --cases 1-112 --out results\gt_eval_fixcn.json default=results/v3/analysis/prompt_only both_fixes=results/v3_native_ade/analysis/prompt_only both_fixes_cn=results/v3_native_ade_cn/analysis/prompt_only k1_both_fixes_cn=results/v3_native_ade_cn/analysis/k1 > jobs\gt_eval_fixcn.txt 2>&1
..\.venv\Scripts\python.exe -u compare_runs.py --a results/rw_core/analysis --b results/rw_native_ade_cn/analysis --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175,181,187,193,199,205,211,217,223,229,235,241,247,253,259,265,271,277,283,289,295,301,307,313,319,325,331,337,343,349,355,361 --names default,both_fixes_cn > jobs\compare_rw_fixcn.txt 2>&1
..\.venv\Scripts\python.exe -u compare_runs.py --a results/rw_native_ade/analysis --b results/rw_native_ade_cn/analysis --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175,181,187,193,199,205,211,217,223,229,235,241,247,253,259,265,271,277,283,289,295,301,307,313,319,325,331,337,343,349,355,361 --names both_fixes,both_fixes_cn >> jobs\compare_rw_fixcn.txt 2>&1
echo FIXCN_COMPLETE %date% %time% >> jobs\fixcn.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\fixcn.log

