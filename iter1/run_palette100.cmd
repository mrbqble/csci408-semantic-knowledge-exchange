@echo off
cd /d C:\Users\mrbqble\Desktop\csci408-probe\iter1
set PYTHONUNBUFFERED=1
echo START %date% %time% > results\palette100.log
..\.venv\Scripts\python.exe -u palette_eval.py --components data\components_m2f --originals data\cityscapes_val --step 5 --limit 100 --out results\iteration1_palette_eval_100.json --save-dir results\palette100 >> results\palette100.log 2>&1
echo EXIT %errorlevel% %date% %time% >> results\palette100.log
