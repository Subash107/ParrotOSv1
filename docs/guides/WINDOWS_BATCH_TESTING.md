# Windows Batch Testing

This guide covers the local Windows batch helpers that validate the main lab findings and generate a report under `reports/`.

The batch runner now uses the shared scenario engine in `tools/run_lab_scenario.py`, so the Windows flow, CI workflow, and markdown reports all read the same challenge catalog from `labs/`.

## What the scripts cover

- service health checks
- app login cookie flag capture
- weak JWT login capture
- forged JWT privilege escalation on `GET /api/admin`
- legitimate admin API overexposure on `GET /api/admin`
- IDOR on `GET /api/user?id=`
- broken admin access on `GET /export`
- reflected XSS on `/profile`
- stored XSS in the comment feed
- MinIO public object exposure and configured default credentials

## Scripts

- `tools/run_lab_scenario.py`
- `tools/generate_mode_comparison_dashboard.py`
- `scripts/windows/check_health.bat`
- `scripts/windows/check_jwt_login.bat`
- `scripts/windows/check_idor.bat`
- `scripts/windows/check_admin_export.bat`
- `scripts/windows/check_reflected_xss.bat`
- `scripts/windows/check_stored_xss.bat`
- `scripts/windows/check_storage.bat`
- `scripts/windows/generate_mode_comparison.bat`
- `scripts/windows/run_local_lab_tests.bat`

## Run everything

From the project root. If you need to change directories first, an example path is:

```powershell
cd d:\ParrotOS\localbugbountylabendtoend
.\scripts\windows\run_local_lab_tests.bat
```

This creates a timestamped directory like:

```text
reports/windows-test-run_20260326_231500/
```

By default, the runner keeps only the newest `10` `windows-test-run_*` folders and removes older ones automatically.

Inside that directory you will find:

- `raw/` with the captured request evidence
- `summary.json`
- `AUTOMATED_WINDOWS_TEST_REPORT.md`
- `FILLED_BUG_BOUNTY_REPORT.md`
- `LAB_REWARD_SCORECARD.md`
- `WALKTHROUGH_FLAGS.md`

## Run one check at a time

You can also call the shared runner directly or call any individual batch file:

```powershell
python .\tools\run_lab_scenario.py --report-root .\reports\manual-scenario --profile vulnerable --capture-source live --compose-file .\docker-compose.yml
.\scripts\windows\check_idor.bat
.\scripts\windows\check_admin_export.bat
```

To validate the fixed-mode stack from the same batch runner, first start the remediated compose stack and then switch the scenario profile for that shell:

```powershell
docker compose -f .\docker-compose.yml -f .\docker-compose.remediated.yml up --build -d
$env:LAB_SCENARIO_PROFILE = "remediated"
.\scripts\windows\run_local_lab_tests.bat
```

After you have both report roots, generate the side-by-side comparison dashboard:

```powershell
.\scripts\windows\generate_mode_comparison.bat
```

With no extra arguments, the batch wrapper auto-detects the best vulnerable/remediated summary pair already present under `reports\`.

You can also point it at custom report roots:

```powershell
.\scripts\windows\generate_mode_comparison.bat .\reports\windows-vulnerable .\reports\windows-remediated .\reports\mode-comparison
```

The comparison output folder contains:

- `COMPARISON_DASHBOARD.html`
- `COMPARISON_SUMMARY.md`
- `comparison.json`

## Notes

- The XSS scripts verify that the payload is reflected or stored in the returned HTML. They do not try to automate a browser popup.
- The storage helper captures the MinIO console page, the public object, and the configured MinIO root credentials from the running container.
- The reward scorecard and filled bug bounty report are meant for training and study, not real-world submission.
- The walkthrough flags file adds a CTF-style progression layer with beginner, intermediate, and advanced challenge guidance.
- The shared manifests live in `labs/challenges/` and `labs/profiles/` if you want to add a new scenario without editing multiple scripts.
- `docker-compose.remediated.yml` starts the same lab in fixed mode so the `remediated` profile can confirm the old exploit checks no longer reproduce.
- The comparison dashboard works with any two folders that already contain `summary.json`, including timestamped Windows runs.
- To keep a different number of recent runs, set `KEEP_WINDOWS_REPORTS` before launching the batch runner. Example: `$env:KEEP_WINDOWS_REPORTS = "10"`.
- To turn the cleanup off for one shell session, set `$env:KEEP_WINDOWS_REPORTS = "0"` before running the batch file.
