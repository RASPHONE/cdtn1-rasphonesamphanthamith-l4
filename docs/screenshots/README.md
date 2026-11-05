# Screenshots — evidence for `docs/test-report.md`

One terminal screenshot per Test Report case, named after the case: `TC-01.png` … `TC-12.png`.
Each shows the command (`pytest -s -v tests/bt3 -k tc01`), the API calls it made, the
`observed:` line and PASSED/FAILED. A case that failed in run 1 (commit `cf58fa7`, before the
fixes) also has `TC-xx-run1.png`.
