@echo off
setlocal EnableExtensions
call "%~dp0common_env.bat" "%~1"

set "FAILURES=0"
echo %LOG_PREFIX% Running health checks...

call :capture "%APP_URL%/" "app_home"
call :capture "%APP_URL%/health" "app_health"
call :capture "%API_URL%/health" "api_health"
call :capture "%ADMIN_URL%/health" "admin_health"
call :capture "%STORAGE_CONSOLE_URL%/" "storage_console_home"
call :capture "%STORAGE_API_URL%/public-assets/security-note.txt" "storage_public_object"

echo %LOG_PREFIX% Health checks complete.
exit /b %FAILURES%

:capture
set "URL=%~1"
set "NAME=%~2"
curl.exe -sS -L "%URL%" ^
  -D "%RAW_DIR%\%NAME%.headers.txt" ^
  -o "%RAW_DIR%\%NAME%.body.txt" ^
  -w "%%{http_code}" > "%RAW_DIR%\%NAME%.status.txt"
if errorlevel 1 (
  > "%RAW_DIR%\%NAME%.status.txt" echo curl_failed
  set /a FAILURES+=1
)
goto :eof
