@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\stage2.log
..\.venv\Scripts\python.exe -u coordinator.py --payloads data\carla_v2_payloads --out results\pilot_cs --variants k1,prompt_only,ipa_recon@0.3,ipa_recon@0.5,ipa_seg@0.2 --k1-cams all --cases 1-24 --palette cs >> jobs\stage2.log 2>&1
..\.venv\Scripts\python.exe -u analysis.py --out results\pilot_cs --dataset C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd --payloads data\carla_v2_payloads --variants k1,prompt_only,ipa_recon_s0.3,ipa_recon,ipa_seg_s0.2 >> jobs\stage2.log 2>&1
echo EXIT %errorlevel% %date% %time% >> jobs\stage2.log

