# Windows Batch Testing

This guide covers the local Windows batch helpers that validate the main lab findings and generate a report under `reports/`.

## What the scripts cover

- service health checks
- weak JWT login capture
- IDOR on `GET /api/user?id=`
- broken admin access on `GET /export`
- reflected XSS on `/profile`
- stored XSS in the comment feed
- MinIO public object exposure and configured default credentials

## Scripts

- `scripts/windows/check_health.bat`
- `scripts/windows/check_jwt_login.bat`
- `scripts/windows/check_idor.bat`
- `scripts/windows/check_admin_export.bat`
- `scripts/windows/check_reflected_xss.bat`
- `scripts/windows/check_stored_xss.bat`
- `scripts/windows/check_storage.bat`
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

You can also call any individual batch file directly:

```powershell
.\scripts\windows\check_idor.bat
.\scripts\windows\check_admin_export.bat
```

## Notes

- The XSS scripts verify that the payload is reflected or stored in the returned HTML. They do not try to automate a browser popup.
- The storage helper captures the MinIO console page, the public object, and the configured MinIO root credentials from the running container.
- The reward scorecard and filled bug bounty report are meant for training and study, not real-world submission.
- The walkthrough flags file adds a CTF-style progression layer with beginner, intermediate, and advanced challenge guidance.
- To keep a different number of recent runs, set `KEEP_WINDOWS_REPORTS` before launching the batch runner. Example: `$env:KEEP_WINDOWS_REPORTS = "10"`.
- To turn the cleanup off for one shell session, set `$env:KEEP_WINDOWS_REPORTS = "0"` before running the batch file.
