<#
DC-GUARDIAN one-time setup on Windows (PowerShell). See docs/INSTALLATION_AND_USER_GUIDE.md.

Prerequisites (install first): Git with Git LFS, Python 3.12, Node.js 20 or newer, and a running
Neo4j (tested with 2026.08, for example in Neo4j Desktop) whose password you know.

    powershell -ExecutionPolicy Bypass -File setup.ps1            # main environment only (CPU)
    powershell -ExecutionPolicy Bypass -File setup.ps1 -Gpu       # also .venv-ppe (NVIDIA GPU for PPE)
    powershell -ExecutionPolicy Bypass -File setup.ps1 -Face      # also .venv-face
    ... -SkipRag  (no download of the approved knowledge documents) / -SkipDemo (no demo data)

Safe to re-run: finished steps are skipped or repeated harmlessly. Nothing is sent to OpenAI.
#>
param([switch]$Gpu, [switch]$Face, [switch]$SkipRag, [switch]$SkipDemo)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Py = Join-Path $PSScriptRoot ".venv-dc-guardian\Scripts\python.exe"
$env:PYTHONPATH = $PSScriptRoot  # project scripts import the repository packages
function Step($text) { Write-Host "`n=== $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "SETUP STOPPED: $text" -ForegroundColor Red; exit 1 }
function Run($exe, [string[]]$arguments) { & $exe @arguments; if ($LASTEXITCODE -ne 0) { Fail "$exe $($arguments -join ' ') failed (exit $LASTEXITCODE)" } }

Step "1/8 Check prerequisites"
foreach ($tool in "git", "node", "npm") { if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail "$tool is not installed or not on PATH" } }
& git lfs version *> $null; if ($LASTEXITCODE -ne 0) { Fail "Git LFS is not installed (https://git-lfs.com), then run: git lfs install" }
$base = $null
if (Get-Command py -ErrorAction SilentlyContinue) { & py -3.12 -c "import sys" *> $null; if ($LASTEXITCODE -eq 0) { $base = @("py", "-3.12") } }
if (-not $base -and (Get-Command python -ErrorAction SilentlyContinue)) { $v = & python -c "import sys;print(f'{sys.version_info[0]}.{sys.version_info[1]}')"; if ($v -eq "3.12") { $base = @("python") } }
if (-not $base -and -not (Test-Path $Py)) { Fail "Python 3.12 is required (https://www.python.org/downloads/)" }
$nodeMajor = [int]((& node --version).TrimStart("v").Split(".")[0]); if ($nodeMajor -lt 20) { Fail "Node.js 20 or newer is required (found $(& node --version))" }
$baseArgs = @(); if ($base -and $base.Count -gt 1) { $baseArgs = $base[1..($base.Count - 1)] }
Write-Host "OK"

Step "2/8 Fetch large model files (Git LFS)"
Run "git" @("lfs", "pull")
$rf = "evidence\predictive_maintenance\models\rf\temporal_rf_v2.joblib"
if ((Get-Item $rf).Length -lt 1MB) { Fail "$rf is still an LFS pointer. If you downloaded a ZIP, clone with git instead (see the guide)." }
Write-Host "OK ($([int]((Get-Item $rf).Length / 1MB)) MB maintenance model present)"

Step "3/8 Python environments"
if (-not (Test-Path $Py)) { Run $base[0] @($baseArgs + @("-m", "venv", ".venv-dc-guardian")) }
Run $Py @("-m", "pip", "install", "--upgrade", "pip")
Run $Py @("-m", "pip", "install", "-r", "requirements.txt")
foreach ($opt in @(@{On = $Gpu; Dir = ".venv-ppe"; Req = "requirements-ppe.txt"}, @{On = $Face; Dir = ".venv-face"; Req = "requirements-face.txt"})) {
    if ($opt.On) {
        $p = Join-Path $PSScriptRoot "$($opt.Dir)\Scripts\python.exe"
        if (-not (Test-Path $p)) { Run $base[0] @($baseArgs + @("-m", "venv", $opt.Dir)) }
        Run $p @("-m", "pip", "install", "-r", $opt.Req)
    }
}

Step "4/8 Local settings (.env)"
if (-not (Test-Path ".env")) {
    $neo = Read-Host "Neo4j password (the one you set in Neo4j)"
    $dash = Read-Host "Choose a password for the DC-GUARDIAN dashboard login (user: operator)"
    (Get-Content ".env.example") `
        -replace '^NEO4J_URI=$', 'NEO4J_URI=bolt://127.0.0.1:7687' -replace '^NEO4J_USER=$', 'NEO4J_USER=neo4j' `
        -replace '^NEO4J_PASSWORD=$', "NEO4J_PASSWORD=$neo" -replace '^NEO4J_DATABASE=$', 'NEO4J_DATABASE=neo4j' `
        -replace '^DCG_LOCAL_USER=$', 'DCG_LOCAL_USER=operator' -replace '^DCG_LOCAL_PASSWORD=$', "DCG_LOCAL_PASSWORD=$dash" `
        -replace '^DCG_LOCAL_ROLE=$', 'DCG_LOCAL_ROLE=administrator' -replace '^DCG_LOCAL_ZONES=$', 'DCG_LOCAL_ZONES=ZONE-A,ZONE-B,ZONE-C' |
        Set-Content -Encoding utf8 ".env"
    Write-Host "Created .env (the AI Investigator stays off; see the guide to enable it with your own OpenAI key)."
} else { Write-Host "Keeping the existing .env" }

Step "5/8 Frontend packages"
Push-Location "presentation\frontend"; try { Run "npm" @("ci") } finally { Pop-Location }

Step "6/8 Neo4j: load the DC-01 data-centre topology"
Run $Py @("-c", "from reasoning.graph.ingest_event import create_driver; d=create_driver(); d.verify_connectivity(); d.close(); print('Neo4j reachable')")
Run $Py @("reasoning\graph\load_topology.py")

Step "7/8 Approved knowledge for the RAG specialists"
if ($SkipRag) { Write-Host "Skipped (-SkipRag): specialists will report that approved knowledge is unavailable." } else {
    # The locked source snapshots ship in knowledge_base\bundled (see its README): CISA refuses automated
    # downloads and live web pages change, so fetch_sources verifies these copies instead of downloading.
    $originals = "response\rag\knowledge_base\originals"
    New-Item -ItemType Directory -Force $originals | Out-Null
    Get-ChildItem "response\rag\knowledge_base\bundled" -File | Where-Object { $_.Name -ne "README.md" } |
        ForEach-Object { if (-not (Test-Path (Join-Path $originals $_.Name))) { Copy-Item $_.FullName $originals } }
    & $Py "response\rag\fetch_sources.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Some approved documents failed verification or download (listed as FAIL above); the index is built from the others." -ForegroundColor Yellow
        Write-Host "See Troubleshooting in docs\INSTALLATION_AND_USER_GUIDE.md." -ForegroundColor Yellow
    }
    foreach ($s in "parse_sources", "preprocess_sources", "chunk_sources", "build_index") { Run $Py @("response\rag\$s.py") }
}

Step "8/8 Demo data"
if ($SkipDemo) { Write-Host "Skipped (-SkipDemo)." } else { Run $Py @("demo_data\load_demo_data.py") }

Write-Host "`nSETUP COMPLETE." -ForegroundColor Green
Write-Host "Start the backend:   .venv-dc-guardian\Scripts\python.exe -m uvicorn presentation.backend.app.main:app --host 127.0.0.1 --port 8000"
Write-Host "Start the frontend:  cd presentation\frontend; npm run dev     then open http://localhost:5173 (user: operator)"
