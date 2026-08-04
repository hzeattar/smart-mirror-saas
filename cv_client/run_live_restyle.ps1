param(
    [string]$ApiUrl = "https://smart-mirror-saas-production.up.railway.app",
    [string]$PairingCode = "",
    [int]$MaxSeconds = 20,
    [int]$ProxyPort = 8787,
    [int]$WebPort = 5174
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogRoot = Join-Path $RepoRoot ".smart-mirror\logs"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

if (-not $env:FAL_KEY) {
    throw "FAL_KEY is missing. Rotate the exposed fal key, then set a new key with: `$env:FAL_KEY='NEW_ROTATED_FAL_KEY'"
}

$MaxSeconds = [Math]::Max(1, [Math]::Min(20, $MaxSeconds))
$env:FAL_PROXY_HOST = "127.0.0.1"
$env:FAL_PROXY_PORT = "$ProxyPort"
$env:LIVE_RESTYLE_MODEL = "decart/lucy2-vton/realtime"
$env:LIVE_RESTYLE_MAX_SECONDS = "$MaxSeconds"

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ProxyOut = Join-Path $LogRoot "fal-proxy-$Timestamp.out.log"
$ProxyErr = Join-Path $LogRoot "fal-proxy-$Timestamp.err.log"
$WebOut = Join-Path $LogRoot "live-restyle-web-$Timestamp.out.log"
$WebErr = Join-Path $LogRoot "live-restyle-web-$Timestamp.err.log"

Push-Location $RepoRoot
try {
    $proxy = Start-Process -FilePath "node" `
        -ArgumentList @(".\tools\fal-proxy\server.mjs") `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $ProxyOut `
        -RedirectStandardError $ProxyErr `
        -PassThru

    $web = Start-Process -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$WebPort") `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $WebOut `
        -RedirectStandardError $WebErr `
        -PassThru

    Start-Sleep -Seconds 5
    $url = "http://127.0.0.1:$WebPort/live-restyle?apiUrl=$([uri]::EscapeDataString($ApiUrl))&maxSeconds=$MaxSeconds"
    if ($PairingCode) {
        $url = "$url&pairingCode=$([uri]::EscapeDataString($PairingCode))"
    }
    Start-Process $url

    Write-Host "Live Restyle kiosk opened: $url"
    Write-Host "fal proxy log: $ProxyOut"
    Write-Host "web log: $WebOut"
    Write-Host "Press Enter to stop the local proxy and web server."
    [void][Console]::ReadLine()
}
finally {
    foreach ($process in @($proxy, $web)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Pop-Location
}
