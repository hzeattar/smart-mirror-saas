# Phase 1 Acceptance Evidence

Automated evidence and Windows hardware evidence will be appended here before merge.

## Automated
- GitHub Actions workflow: `.github/workflows/phase-1-real-garments.yml`
- 2026-07-29 local Windows: Python tracked-source compile with `py_compile`: passed.
- 2026-07-29 local Windows: full CV unittest discovery: 26 tests passed.
- 2026-07-29 local Windows: Laravel feature tests: 6 tests / 38 assertions passed.
- 2026-07-29 local Windows: `npm run build`: passed.
- 2026-07-29 local Windows: `vendor/bin/pint --test`: passed.
- 2026-07-29 local Windows: `PhotographicGarmentCatalogSeeder.php` and `DatabaseSeeder.php` syntax checks: passed.
- 2026-07-29 fix: PHPUnit now forces isolated sqlite in-memory test settings and clears `DATABASE_URL`/`DB_URL`, preventing host-level database URLs from leaking into tests.

## Hardware
Pending target Windows webcam acceptance.

## Railway
Pending merge/deploy verification; no Phase 1 Railway deployment has been claimed.
