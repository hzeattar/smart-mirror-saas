param(
    [string]$ApiUrl = "https://smart-mirror-saas-production.up.railway.app",
    [string]$DeviceName = "Main Store Mirror",
    [int]$Camera = 0,
    [int]$Width = 640,
    [int]$Height = 360,
    [ValidateSet("auto", "dshow", "msmf", "any")]
    [string]$CameraBackend = "dshow",
    [switch]$NoGestureDebug,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$LogDir = Join-Path $PSScriptRoot ".smart-mirror\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Transcript = Join-Path $LogDir ("kiosk-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

Start-Transcript -Path $Transcript | Out-Null
try {
    $Args = @(
        (Join-Path $PSScriptRoot "main.py"),
        "--api-url", $ApiUrl,
        "--device-name", $DeviceName,
        "--camera", "$Camera",
        "--camera-backend", $CameraBackend,
        "--width", "$Width",
        "--height", "$Height",
        "--ai-tryon",
        "--experience", "hybrid",
        "--hybrid-auto-start",
        "--kiosk-health-hud"
    )
    if (-not $NoGestureDebug) {
        $Args += "--gesture-debug"
    }

    do {
        $startedAt = Get-Date
        Write-Host "Starting Smart Mirror kiosk at $($startedAt.ToString('s'))"
        & $Python @Args
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0 -or $NoRestart) {
            break
        }
        Write-Warning "Smart Mirror exited with code $exitCode. Restarting in 5 seconds..."
        Start-Sleep -Seconds 5
    } while ($true)
} finally {
    Stop-Transcript | Out-Null
}
