# Free Google Drive quota (22 Nov 2026): remove Drive copies whose originals stay on the OMEN.
# Every Drive item is deleted only after its local original is found with at least as many files.
$ErrorActionPreference = 'Continue'
$SPW = 'C:\Users\mrbqble\My Drive (bibol.assetbek@nu.edu.kz)\uni\04\01\CSCI 408\Senior Project Work'
$PO  = "$SPW\Pipeline Outputs"
$K   = 'C:\carla_multicam_kit\output'
$P   = 'C:\Users\mrbqble\Desktop\csci408-probe'
$LOG = "$P\iter2\jobs\drive_free.log"
"FREE_START $(Get-Date)" | Out-File $LOG -Encoding utf8
$pairs = New-Object System.Collections.Generic.List[object]
foreach ($t in 'cases_test','smoke_001','v2_test','v2_test2','v2_test3','v2_test4','v3_smoke','rw2_smoke_test','rw2_smoke_test2') { $pairs.Add(@("$SPW\Datasets\_development_tests\$t", "$K\$t", 'tier1 dev tests')) }
$pairs.Add(@("$SPW\Datasets\Real-world\V1\_work", "$K\real_world_astana_3phones_sync_v1\_work", 'tier1 sync thumbnails'))
$pairs.Add(@("$SPW\Datasets\Real-world\V2\_work", "$K\real_world_astana_3phones_sync_v2\_work", 'tier1 sync thumbnails'))
$detector = 'carla_v2','carla_v2_hr','pilot_cs','pilot_ade','hp','tune_c00','tune_c05','tune_c05_hr','tune_c10_hr','refine','v3_2048','geofuse_a10_g1.5','geofuse_a10_g2.5','geofuse_a10_g4.0','geofuse_a30_g1.5','geofuse_a30_g2.5','geofuse_a30_g4.0','v3_geofuse','v3_smoke_geofuse','smoke','v3_smoke'
foreach ($d in $detector) { $pairs.Add(@("$PO\iteration2\results\$d", "$P\iter2\results\$d", 'tier1 detector-era results')) }
$pairs.Add(@("$PO\iteration2\training_crops.zip", "$P\iter2\_scratch\training_crops.zip", 'tier1 training crops'))
$ablation = 'v3_fuseF_st0.3','v3_fuseF_st0.4','v3_fuseF_st0.5','v3_fuseF_st0.6','rw_fuseF_st0.3','rw_fuseF_st0.4','rw_fuseF_st0.5','rw_fuseF_st0.6'
foreach ($d in $ablation) { $pairs.Add(@("$PO\iteration2\results\$d", "$P\iter2\results\$d", 'tier2 full-res supports and tuning')) }
$earlier = 'v3','rw_core','v3_native_ade','rw_native_ade','v3_native_cs','rw_native_cs','v3_ade','rw_ade','v3_native_ade_cn','rw_native_ade_cn','v3_cn07_15','rw_cn07_15','cs_paper'
foreach ($d in $earlier) { $pairs.Add(@("$PO\iteration2\results\$d", "$P\iter2\results\$d", 'tier2 earlier judged receivers')) }
$pairs.Add(@("$PO\iteration1\results", "$P\iter1\results", 'tier2 iteration 1'))
foreach ($c in 'components_m2f','components_seg1024','components_seg512') { $pairs.Add(@("$PO\iteration1\payloads\$c", "$P\iter1\data\$c", 'tier2 iteration 1')) }
$pairs.Add(@("$PO\iteration1\authors_check", "$P\iter1\authors_check", 'tier2 iteration 1'))

$freed = 0.0
foreach ($p in $pairs) {
    $drive, $orig, $tier = $p[0], $p[1], $p[2]
    if (-not (Test-Path -LiteralPath $drive)) { "SKIP (not on Drive) $drive" | Out-File $LOG -Append -Encoding utf8; continue }
    if (-not (Test-Path -LiteralPath $orig))  { "KEEP (original missing) $drive" | Out-File $LOG -Append -Encoding utf8; continue }
    $dItem = Get-Item -LiteralPath $drive
    if ($dItem.PSIsContainer) {
        $dFiles = @(Get-ChildItem -LiteralPath $drive -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'desktop.ini' })
        $oFiles = @(Get-ChildItem -LiteralPath $orig -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'desktop.ini' })
        $size = ($dFiles | Measure-Object Length -Sum).Sum
        if ($oFiles.Count -lt $dFiles.Count) { "KEEP (original has fewer files: $($oFiles.Count) < $($dFiles.Count)) $drive" | Out-File $LOG -Append -Encoding utf8; continue }
    } else {
        $size = $dItem.Length
        if ((Get-Item -LiteralPath $orig).Length -ne $size) { "KEEP (size differs) $drive" | Out-File $LOG -Append -Encoding utf8; continue }
    }
    Remove-Item -LiteralPath $drive -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $drive) { "FAILED to remove $drive" | Out-File $LOG -Append -Encoding utf8; continue }
    $freed += $size
    ("REMOVED {0,7:N3} GB  [{1}]  {2}" -f ($size/1GB), $tier, $drive.Replace("$SPW\", '')) | Out-File $LOG -Append -Encoding utf8
}
# empty parent folders left behind
foreach ($e in "$SPW\Datasets\_development_tests", "$PO\iteration1\payloads", "$PO\iteration1") {
    if ((Test-Path -LiteralPath $e) -and -not (Get-ChildItem -LiteralPath $e -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'desktop.ini' })) { Remove-Item -LiteralPath $e -Recurse -Force -ErrorAction SilentlyContinue; "REMOVED empty folder $($e.Replace("$SPW\", ''))" | Out-File $LOG -Append -Encoding utf8 }
}
("FREED_TOTAL {0:N2} GB" -f ($freed/1GB)) | Out-File $LOG -Append -Encoding utf8
"FREE_COMPLETE $(Get-Date)" | Out-File $LOG -Append -Encoding utf8
