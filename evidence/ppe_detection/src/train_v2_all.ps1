# Trains the three PPE-v2 candidates one after another (about 12-15 hours on the RTX 3080 Ti).
# Each candidate logs to results/training_v2/<candidate>.log; progress lines go to train_v2_all.log.
# Run detached so it survives the terminal:
#   Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-File','evidence\ppe_detection\src\train_v2_all.ps1'
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
Set-Location $root
$out = Join-Path $root 'evidence\ppe_detection\results\training_v2'
New-Item -ItemType Directory -Force $out | Out-Null
$python = Join-Path $root '.venv-ppe\Scripts\python.exe'
foreach ($candidate in 'v2s1024', 'v2m1024', 'v2n1024') {
    Add-Content (Join-Path $out 'train_v2_all.log') "$(Get-Date -Format s) START $candidate"
    & $python 'evidence\ppe_detection\src\train_v2.py' --candidate $candidate *> (Join-Path $out "$candidate.log")
    Add-Content (Join-Path $out 'train_v2_all.log') "$(Get-Date -Format s) END $candidate exit $LASTEXITCODE"
}
Add-Content (Join-Path $out 'train_v2_all.log') "$(Get-Date -Format s) ALL DONE"
