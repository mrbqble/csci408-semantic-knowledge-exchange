@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\q2.log
set PYTHONIOENCODING=utf-8
:wait
if exist jobs\q1.done goto go
timeout /t 30 /nobreak > nul
goto wait
:go
echo STAGE reports-cpu %date% %time% >> jobs\q2.log
..\.venv\Scripts\python.exe -u refine_full_report.py > jobs\refine_full_report.txt 2>&1
..\.venv\Scripts\python.exe -u gt_eval.py --cases 1-24 --out results\gt_eval_2048.json default=results/v3/analysis/prompt_only big_2048x1152=results/v3_2048/analysis/prompt_only > jobs\gt_eval_2048.txt 2>&1
echo STAGE seg-resolution %date% %time% >> jobs\q2.log
..\.venv\Scripts\python.exe -u seg_resolution.py > jobs\seg_resolution.txt 2>&1
echo STAGE instance-sender %date% %time% >> jobs\q2.log
..\.venv\Scripts\python.exe -u instance_sender.py > jobs\instance_sender.txt 2>&1
echo STAGE hp-sweep %date% %time% >> jobs\q2.log
..\.venv\Scripts\python.exe -u hp_sweep.py > jobs\hp_sweep.txt 2>&1
echo STAGE v4-generate %date% %time% >> jobs\q2.log
cd /d C:\carla_multicam_kit
powershell -NoProfile -Command "Get-Process CarlaUE4* -ErrorAction SilentlyContinue | Stop-Process -Force"
powershell -NoProfile -Command "Start-Process -FilePath C:\CARLA\CARLA_0.9.16\CarlaUE4.exe -ArgumentList '-quality-level=Epic','-carla-rpc-port=2000','-RenderOffScreen' -WorkingDirectory C:\CARLA\CARLA_0.9.16"
powershell -NoProfile -Command "$t = 0; while (-not (Get-NetTCPConnection -LocalPort 2000 -State Listen -ErrorAction SilentlyContinue) -and $t -lt 180) { Start-Sleep 3; $t += 3 }; Start-Sleep 25"
C:\carla_multicam_kit\.venv\Scripts\python.exe -u generate_cases_v3.py --out C:\carla_multicam_kit\output\carla_dataset_v4_train --cases 224 --seed 31 --resume --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12 >> C:\Users\mrbqble\Desktop\csci408-probe\iter2\jobs\v4_gen.log 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\mrbqble\Desktop\csci408-probe\iter2\ops\v4_finish.ps1
powershell -NoProfile -Command "Get-Process CarlaUE4* -ErrorAction SilentlyContinue | Stop-Process -Force"
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
echo STAGE payloads-v4 %date% %time% >> jobs\q2.log
..\.venv\Scripts\python.exe -u payloads.py --dataset C:\carla_multicam_kit\output\carla_dataset_v4_train --out data\v4_payloads >> jobs\q2.log 2>&1
echo STAGE payloads-real-all %date% %time% >> jobs\q2.log
..\.venv\Scripts\python.exe -u payloads.py --dataset C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core --out data\rw_core_all_payloads >> jobs\q2.log 2>&1
echo STAGE training-prep %date% %time% >> jobs\q2.log
..\.venv\Scripts\python.exe -u training_prep.py > jobs\training_prep.txt 2>&1
echo Q2_COMPLETE %date% %time% >> jobs\q2.log
echo done > jobs\q2.done
echo EXIT %errorlevel% %date% %time% >> jobs\q2.log

