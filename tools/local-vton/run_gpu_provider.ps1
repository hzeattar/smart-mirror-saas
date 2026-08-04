param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8788,
    [string]$Model = "idm-vton"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Local VTON evaluation bench"
Write-Host "Host: $Host"
Write-Host "Port: $Port"
Write-Host "Model: $Model"

$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if (-not $nvidia) {
    Write-Warning "nvidia-smi was not found. Install NVIDIA drivers/CUDA before running a real local VTON model."
} else {
    & nvidia-smi
}

Write-Warning "This starts a stub HTTP provider only. Install and license-approve the selected VTON model before commercial use."
python (Join-Path $ScriptRoot "gpu_provider_stub.py") --host $Host --port $Port --model $Model
