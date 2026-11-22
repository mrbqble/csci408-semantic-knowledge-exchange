@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter2
set PYTHONUNBUFFERED=1
echo START %date% %time% > jobs\queue.log
set PYTHONIOENCODING=utf-8
set V2=C:\carla_multicam_kit\output\carla_dataset_v2_low2m_3to6cams_hd
set V3=C:\carla_multicam_kit\output\carla_dataset_v3_ids
set RW=C:\carla_multicam_kit\output\real_world_astana_3phones_sync_v1\core
set PY=C:\Users\mrbqble\Desktop\csci408-probe\.venv\Scripts\python.exe
set IT=C:\Users\mrbqble\Desktop\csci408-probe\iter2
set LOGQ=%IT%\jobs\queue.log
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File %IT%\keepawake_q.ps1
powershell -NoProfile -Command "Get-Process CarlaUE4* -ErrorAction SilentlyContinue | Stop-Process -Force"
echo STAGE v3-generate %date% %time% >> %LOGQ%
cd /d C:\carla_multicam_kit
powershell -NoProfile -Command "if (-not (Get-NetTCPConnection -LocalPort 2000 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath C:\CARLA\CARLA_0.9.16\CarlaUE4.exe -ArgumentList '-quality-level=Epic','-carla-rpc-port=2000','-RenderOffScreen' -WorkingDirectory C:\CARLA\CARLA_0.9.16 }"
powershell -NoProfile -Command "$t = 0; while (-not (Get-NetTCPConnection -LocalPort 2000 -State Listen -ErrorAction SilentlyContinue) -and $t -lt 180) { Start-Sleep 3; $t += 3 }; Start-Sleep 25"
C:\carla_multicam_kit\.venv\Scripts\python.exe -u generate_cases_v3.py --out %V3% --cases 112 --seed 21 --resume --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12 >> %IT%\jobs\v3_gen.log 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File %IT%\v3_finish.ps1
powershell -NoProfile -Command "Get-Process CarlaUE4* -ErrorAction SilentlyContinue | Stop-Process -Force"
cd /d %IT%
echo STAGE v3-pipeline %date% %time% >> %LOGQ%
%PY% -u payloads.py --dataset %V3% --out data\v3_payloads >> %LOGQ% 2>&1
%PY% -u coordinator.py --payloads data\v3_payloads --out results\v3 --variants k1,prompt_only --cases 1-112 --palette cs >> %LOGQ% 2>&1
%PY% -u analysis.py --out results\v3 --dataset %V3% --payloads data\v3_payloads --variants k1,prompt_only >> %LOGQ% 2>&1
%PY% -u geofuse.py --out results\v3_geofuse --manifest %V3%\manifest.json --payloads data\v3_payloads --min-area 10 --gate 2.5 >> %LOGQ% 2>&1
%PY% -u eval_union.py --manifest %V3%\manifest.json --geofuse results\v3_geofuse --analysis results\v3\analysis --variants oracle_gen,k1,prompt_only --out results\v3_eval_union.json > jobs\v3_eval.txt 2>&1
echo STAGE hr-1280x704 %date% %time% >> %LOGQ%
%PY% -u coordinator.py --payloads data\carla_v2_payloads --out results\carla_v2_hr --variants prompt_only --cases 1-112 --palette cs --size 1280x704 >> %LOGQ% 2>&1
%PY% -u analysis.py --out results\carla_v2_hr --dataset %V2% --payloads data\carla_v2_payloads --variants prompt_only --no-overlays >> %LOGQ% 2>&1
%PY% -u compare_hr.py > jobs\hr_compare.txt 2>&1
echo STAGE realworld %date% %time% >> %LOGQ%
%PY% -u payloads.py --dataset %RW% --out data\rw_core_payloads --cases 1,7,13,19,25,31,37,43,49,55,61,67,73,79,85,91,97,103,109,115,121,127,133,139,145,151,157,163,169,175,181,187,193,199,205,211,217,223,229,235,241,247,253,259,265,271,277,283,289,295,301,307,313,319,325,331,337,343,349,355,361 >> %LOGQ% 2>&1
%PY% -u coordinator.py --payloads data\rw_core_payloads --out results\rw_core --variants k1,prompt_only --palette cs >> %LOGQ% 2>&1
%PY% -u analysis.py --out results\rw_core --dataset %RW% --payloads data\rw_core_payloads --variants k1,prompt_only >> %LOGQ% 2>&1
echo STAGE report %date% %time% >> %LOGQ%
%PY% -u make_report.py >> %LOGQ% 2>&1
echo QUEUE_COMPLETE %date% %time% >> %LOGQ%
echo done > jobs\queue.done
echo EXIT %errorlevel% %date% %time% >> jobs\queue.log

