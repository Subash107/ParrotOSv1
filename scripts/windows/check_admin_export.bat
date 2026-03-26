@echo off
setlocal EnableExtensions
call "%~dp0common_env.bat" "%~1"

echo %LOG_PREFIX% Capturing admin export response...
curl.exe -sS -L "%ADMIN_URL%/export" ^
  -H "role: admin" ^
  -D "%RAW_DIR%\admin_export.headers.txt" ^
  -o "%RAW_DIR%\admin_export.json" ^
  -w "%%{http_code}" > "%RAW_DIR%\admin_export.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\admin_export.status.txt" echo curl_failed
  exit /b 1
)

echo %LOG_PREFIX% Admin export capture complete.
exit /b 0
