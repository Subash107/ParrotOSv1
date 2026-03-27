@echo off
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "PROJECT_ROOT=%%~fI"
set "REPORTS_DIR=%PROJECT_ROOT%\reports"
set "COMPOSE_FILE=%PROJECT_ROOT%\docker-compose.yml"
set "LOG_PREFIX=[lab-windows]"
if not defined KEEP_WINDOWS_REPORTS set "KEEP_WINDOWS_REPORTS=10"
if not defined LAB_SCENARIO_PROFILE set "LAB_SCENARIO_PROFILE=vulnerable"
if not exist "%REPORTS_DIR%" mkdir "%REPORTS_DIR%" >nul 2>&1

if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Date).ToString('yyyyMMdd_HHmmss') | Set-Content -Encoding ascii '%REPORTS_DIR%\.windows_run_id.txt'"
  set /p RUN_ID=<"%REPORTS_DIR%\.windows_run_id.txt"
  del "%REPORTS_DIR%\.windows_run_id.txt" >nul 2>&1
  if not defined RUN_ID set "RUN_ID=manual"
) else (
  set "REPORT_ROOT=%~1"
)

if "%~1"=="" set "REPORT_ROOT=%REPORTS_DIR%\windows-test-run_%RUN_ID%"

if not exist "%REPORT_ROOT%" mkdir "%REPORT_ROOT%" >nul 2>&1

set "RAW_DIR=%REPORT_ROOT%\raw"
if not exist "%RAW_DIR%" mkdir "%RAW_DIR%" >nul 2>&1

set "APP_URL=http://localhost:8080"
set "API_URL=http://localhost:8081"
set "ADMIN_URL=http://localhost:8082"
set "STORAGE_API_URL=http://localhost:9000"
set "STORAGE_CONSOLE_URL=http://localhost:9001"

goto :eof
