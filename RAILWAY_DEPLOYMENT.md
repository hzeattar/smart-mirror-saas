# Railway Deployment

This commit intentionally triggers Railway to deploy the complete Smart Mirror SaaS source from the `main` branch.

## Expected build inputs

- `Dockerfile`
- `railway.json`
- `scripts/start.sh`
- Laravel backend and API
- Vue admin dashboard
- Python MediaPipe/OpenCV client source

## Deployment revision

The complete application source was materialized in commit `aade146e488c3907c06709219f56f73c2dda3e21`, followed by Railway runtime hardening commits.

Railway must deploy the latest `main` revision, not any historical `Add source bootstrap chunk` commit.
