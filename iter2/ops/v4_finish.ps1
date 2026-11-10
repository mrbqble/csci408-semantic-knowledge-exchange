$py = "C:\carla_multicam_kit\.venv\Scripts\python.exe"
$out = "C:\carla_multicam_kit\output\carla_dataset_v4_train"
$log = "C:\Users\mrbqble\Desktop\csci408-probe\iter2\jobs\v4_gen_retry.log"
$env:PYTHONIOENCODING = 'utf-8'
Set-Location C:\carla_multicam_kit
foreach ($shift in 4, 2) {
  if (-not (Test-Path "$out\manifest.json")) { break }
  $m = Get-Content "$out\manifest.json" -Raw | ConvertFrom-Json
  $failed = @($m.failed_cases)
  if ($failed.Count -eq 0) { break }
  ("retry shift {0}: cases {1}" -f $shift, ($failed -join ",")) | Add-Content $log
  & $py -u C:\carla_multicam_kit\generate_cases_v3.py --out $out --cases 224 --seed (31 + $shift) --only-cases ($failed -join ",") --junction-shift $shift --vehicles 20,110 --walkers 30,260 --warmup 3 --rounds 12 *>> $log
}

