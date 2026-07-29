# Phase 1 — Windows Hardware Acceptance Checklist

This checklist must be completed before merging `phase-2-real-garments-smart-ui` into `main`.

## Preparation

```powershell
cd C:\Users\AM\Desktop\smart-mirror-saas
git fetch origin
git checkout phase-2-real-garments-smart-ui
git pull origin phase-2-real-garments-smart-ui
cd cv_client
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_model.py
```

## Automated tests

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Expected result: all tests pass without errors.

## Smart UI camera test

```powershell
.\.venv\Scripts\python.exe main.py `
  --api-url "https://smart-mirror-saas-production.up.railway.app" `
  --gesture-debug
```

Confirm:
- pointing with the index finger moves a smooth cursor;
- staying over a control fills the confirmation ring and triggers once;
- a slow hand drift does not change products;
- a deliberate fast swipe changes one product only;
- the product card does not cover the torso;
- keyboard and mouse controls remain usable;
- thumbs-up saves a single photo;
- the camera remains responsive.

## Lower garment test

This test becomes fully available after the photographic catalog is deployed.

Confirm:
- trousers are never rendered over the chest;
- when hips or feet are outside the frame, the UI asks the customer to step back;
- trousers render only after hips, knees and ankles are visible;
- an incomplete trouser frame cannot be saved.

## Photographic asset test after Railway deployment

Confirm:
- five photographic products are returned by the deployed catalog;
- legacy cartoon products are inactive;
- the first load prepares and caches a transparent PNG;
- subsequent product loads use `.smart-mirror/garment-cache`;
- name, price and size chart match the admin dashboard;
- all source/licence metadata is available in the repository.
