# PowerShell ortak yardimcilari (demo/senaryo/*.ps1 icin)
# Windows ortaminda dogrudan calistirilabilir.
$ErrorActionPreference = "Stop"

$DEMO_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$REPO_ROOT = Split-Path -Parent (Split-Path -Parent $DEMO_DIR)
$COMPOSE_FILE = Join-Path $REPO_ROOT "deploy\compose.yaml"
$API_BASE = if ($env:GRIDUP_API) { $env:GRIDUP_API } else { "http://localhost:8000" }
$FRONTEND_BASE = if ($env:GRIDUP_FRONTEND) { $env:GRIDUP_FRONTEND } else { "http://localhost:3000" }
$MQTT_TARGET = if ($env:GRIDUP_MQTT) { $env:GRIDUP_MQTT } else { "localhost:1883" }

function Write-Title($text) {
    Write-Host "`n== $text ==" -ForegroundColor Blue
}

function Write-Success($text) {
    Write-Host "✓ $text" -ForegroundColor Green
}

function Write-WarningMsg($text) {
    Write-Host "! $text" -ForegroundColor Yellow
}

function Write-ErrorMsg($text) {
    Write-Host "✗ $text" -ForegroundColor Red
}

function Test-StackHealth() {
    try {
        $res = Invoke-RestMethod -Uri "$API_BASE/health" -Method Get -TimeoutSec 3 -ErrorAction Stop
        Write-Success "Backend ayakta ($API_BASE)"
        return $true
    } catch {
        Write-ErrorMsg "Backend $API_BASE/health yanit vermiyor. Once sunu calistirin:"
        Write-Host "  docker compose -f '$COMPOSE_FILE' up -d --build"
        return $false
    }
}

function Find-Python() {
    if ($env:GRIDUP_PYTHON) { return $env:GRIDUP_PYTHON }
    $candidates = @("py", "python", "python3")
    foreach ($cand in $candidates) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if ($cmd) {
            try {
                if ($cand -eq "py") {
                    $null = & py -3 -c "import sys" 2>$null
                    if ($LASTEXITCODE -eq 0) { return "py -3" }
                } else {
                    $null = & $cand -c "import sys" 2>$null
                    if ($LASTEXITCODE -eq 0) { return $cand }
                }
            } catch {}
        }
    }
    return $null
}

# PYTHONPATH'e libs/panoalgo ekle
$algoPath = Join-Path $REPO_ROOT "libs\panoalgo"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$algoPath;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $algoPath
}

function Run-Scenario($scenario, $pano, $duration, $extraArgs = @()) {
    $py = Find-Python
    if (-not $py) {
        Write-WarningMsg "Python bulunamadi. Lutfen Python 3.12+ yukleyin veya GRIDUP_PYTHON degiskenini ayarlayin."
        Write-Host "  Alternatif: cd frontend && npm run dev:mock (tarayicida $FRONTEND_BASE adresine gidin)"
        return $false
    }

    $simScript = Join-Path $REPO_ROOT "sim\panosim.py"
    Write-Success "Senaryo oynatiliyor (host Python): $pano, $scenario, ${duration} sn"

    $argList = @("$simScript", "--scenario", "$scenario", "--pano", "$pano", "--duration", "$duration", "--mqtt", "$MQTT_TARGET") + $extraArgs
    if ($py -eq "py -3") {
        & py -3 @argList
    } else {
        & $py @argList
    }
    return ($LASTEXITCODE -eq 0)
}
