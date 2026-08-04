# Local VTON Evaluation Bench

This path is an evaluation scaffold for a second Windows machine with an NVIDIA GPU.
It is not enabled for production kiosk sessions by default.

Open-source VTON projects often carry non-commercial licenses, so use this bench only
for quality experiments unless the selected model and weights are approved for the
store's commercial use.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\local-vton\run_gpu_provider.ps1 `
  -Host 0.0.0.0 `
  -Port 8788 `
  -Model idm-vton
```
