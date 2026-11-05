# Screenshots — evidence for `docs/test-report.md`

One terminal screenshot per Test Report case, named after the case: `TC-01.png` … `TC-12.png`.
Each shows the command (`DB_PORT=5433 pytest -s -v tests/bt3 -k tc01`), the API calls it made,
the `observed:` line and PASSED/FAILED. The three cases that failed before the fixes also have
`TC-08-run1.png`, `TC-09-run1.png` and `TC-11-run1.png` (commit `cf58fa7`).
`full-suite.png` is the whole suite with the README command: `pytest -q` → 98 passed.
