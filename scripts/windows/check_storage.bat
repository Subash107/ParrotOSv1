@echo off
setlocal EnableExtensions
call "%~dp0common_env.bat" "%~1"

set "FAILURES=0"
echo %LOG_PREFIX% Capturing storage exposure evidence...

curl.exe -sS -L "%STORAGE_CONSOLE_URL%/" ^
  -D "%RAW_DIR%\storage_console.headers.txt" ^
  -o "%RAW_DIR%\storage_console.html" ^
  -w "%%{http_code}" > "%RAW_DIR%\storage_console.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\storage_console.status.txt" echo curl_failed
  set /a FAILURES+=1
)

curl.exe -sS -L "%STORAGE_API_URL%/public-assets/security-note.txt" ^
  -D "%RAW_DIR%\storage_public_object_check.headers.txt" ^
  -o "%RAW_DIR%\storage_public_object_check.txt" ^
  -w "%%{http_code}" > "%RAW_DIR%\storage_public_object_check.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\storage_public_object_check.status.txt" echo curl_failed
  set /a FAILURES+=1
)

docker compose -f "%COMPOSE_FILE%" exec -T storage env > "%RAW_DIR%\storage_env.txt"
if errorlevel 1 (
  > "%RAW_DIR%\storage_env.status.txt" echo docker_exec_failed
  set /a FAILURES+=1
) else (
  > "%RAW_DIR%\storage_env.status.txt" echo 0
)

echo %LOG_PREFIX% Storage evidence capture complete.
exit /b %FAILURES%
