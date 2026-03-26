@echo off
setlocal EnableExtensions
call "%~dp0common_env.bat" "%~1"

set "SCRIPT_FAILURES=0"
echo %LOG_PREFIX% Report root: "%REPORT_ROOT%"

docker compose -f "%COMPOSE_FILE%" ps --format json > "%RAW_DIR%\docker_compose_ps.json"
findstr /r "." "%RAW_DIR%\docker_compose_ps.json" >nul
if errorlevel 1 (
  echo %LOG_PREFIX% No lab containers are running.
  echo %LOG_PREFIX% Start the stack with: docker compose up --build -d
  exit /b 1
)

call "%~dp0check_health.bat" "%REPORT_ROOT%"
if errorlevel 1 set /a SCRIPT_FAILURES+=1

call "%~dp0check_jwt_login.bat" "%REPORT_ROOT%"
if errorlevel 1 set /a SCRIPT_FAILURES+=1

call "%~dp0check_idor.bat" "%REPORT_ROOT%"
if errorlevel 1 set /a SCRIPT_FAILURES+=1

call "%~dp0check_admin_export.bat" "%REPORT_ROOT%"
if errorlevel 1 set /a SCRIPT_FAILURES+=1

call "%~dp0check_reflected_xss.bat" "%REPORT_ROOT%"
if errorlevel 1 set /a SCRIPT_FAILURES+=1

call "%~dp0check_stored_xss.bat" "%REPORT_ROOT%"
if errorlevel 1 set /a SCRIPT_FAILURES+=1

call "%~dp0check_storage.bat" "%REPORT_ROOT%"
if errorlevel 1 set /a SCRIPT_FAILURES+=1

python "%PROJECT_ROOT%\tools\generate_windows_test_report.py" --report-root "%REPORT_ROOT%"
if errorlevel 1 (
  py -3 "%PROJECT_ROOT%\tools\generate_windows_test_report.py" --report-root "%REPORT_ROOT%"
)

if errorlevel 1 (
  echo %LOG_PREFIX% Report generation failed.
  exit /b 1
)

python "%PROJECT_ROOT%\tools\generate_learning_lab_report.py" --report-root "%REPORT_ROOT%"
if errorlevel 1 (
  py -3 "%PROJECT_ROOT%\tools\generate_learning_lab_report.py" --report-root "%REPORT_ROOT%"
)

if errorlevel 1 (
  echo %LOG_PREFIX% Learning asset generation failed.
  exit /b 1
)

call :cleanup_old_windows_runs
if errorlevel 1 (
  echo %LOG_PREFIX% Automatic cleanup skipped because the retention step failed.
) else (
  for /f "usebackq delims=" %%I in ("%RAW_DIR%\cleanup_windows_runs.txt") do echo %LOG_PREFIX% %%I
)

echo %LOG_PREFIX% Report generated:
echo %LOG_PREFIX%   "%REPORT_ROOT%\AUTOMATED_WINDOWS_TEST_REPORT.md"
echo %LOG_PREFIX%   "%REPORT_ROOT%\summary.json"
echo %LOG_PREFIX%   "%REPORT_ROOT%\FILLED_BUG_BOUNTY_REPORT.md"
echo %LOG_PREFIX%   "%REPORT_ROOT%\LAB_REWARD_SCORECARD.md"
echo %LOG_PREFIX%   "%REPORT_ROOT%\WALKTHROUGH_FLAGS.md"
exit /b %SCRIPT_FAILURES%

:cleanup_old_windows_runs
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$reportsRoot = [System.IO.Path]::GetFullPath($env:REPORTS_DIR);" ^
  "$keep = 10;" ^
  "try { if ($env:KEEP_WINDOWS_REPORTS -and $env:KEEP_WINDOWS_REPORTS.Trim().Length -gt 0) { $keep = [int]$env:KEEP_WINDOWS_REPORTS } } catch { $keep = 10 };" ^
  "if ($keep -lt 0) { $keep = 10 }" ^
  "if ($keep -eq 0) { 'Automatic cleanup disabled.' | Set-Content -Encoding ascii $env:RAW_DIR\\cleanup_windows_runs.txt; exit 0 }" ^
  "$runs = Get-ChildItem -LiteralPath $reportsRoot -Directory | Where-Object { $_.Name -like 'windows-test-run_*' } | Sort-Object LastWriteTime -Descending;" ^
  "$toRemove = $runs | Select-Object -Skip $keep;" ^
  "foreach ($dir in $toRemove) { $full = [System.IO.Path]::GetFullPath($dir.FullName); if (-not $full.StartsWith($reportsRoot, [System.StringComparison]::OrdinalIgnoreCase)) { throw ('Refusing to delete outside reports root: ' + $full) }; Remove-Item -LiteralPath $full -Recurse -Force }" ^
  "('Kept newest ' + $keep + ' windows report folders; removed ' + $toRemove.Count + ' older folder(s).') | Set-Content -Encoding ascii $env:RAW_DIR\\cleanup_windows_runs.txt"
if errorlevel 1 exit /b 1
exit /b 0
