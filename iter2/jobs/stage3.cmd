@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\stage3.log
copy /Y results\pilot_cs\analysis\summary.json results\pilot_cs\analysis\summary_stage2_backup.json > nul
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\pilot_cs --variants prompt_shuffled --cases 1-24 --palette cs >> jobs\stage3.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\pilot_cs --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --payloads data\carla_v2_payloads --variants k1,prompt_only,prompt_shuffled,ipa_recon_s0.3,ipa_recon,ipa_seg_s0.2 --no-overlays >> jobs\stage3.log 2>&1
robocopy results\pilot_cs\k1 results\carla_v2\k1 *_cam1.png *_cam1.json /NFL /NDL /NJH /NJS >> jobs\stage3.log 2>&1
robocopy results\pilot_cs\prompt_only results\carla_v2\prompt_only *.png *.json /NFL /NDL /NJH /NJS >> jobs\stage3.log 2>&1
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\carla_v2 --variants k1,prompt_only --cases 1-112 --palette cs >> jobs\stage3.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\carla_v2 --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --payloads data\carla_v2_payloads --variants k1,prompt_only >> jobs\stage3.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\stage3.log

