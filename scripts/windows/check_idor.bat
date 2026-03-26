@echo off
setlocal EnableExtensions
call "%~dp0common_env.bat" "%~1"

set "FAILURES=0"
echo %LOG_PREFIX% Capturing IDOR evidence...

for %%I in (1 2 3) do (
  curl.exe -sS -L "%API_URL%/api/user?id=%%I" ^
    -D "%RAW_DIR%\idor_user_%%I.headers.txt" ^
    -o "%RAW_DIR%\idor_user_%%I.json" ^
    -w "%%{http_code}" > "%RAW_DIR%\idor_user_%%I.status.txt"
  if errorlevel 1 (
    > "%RAW_DIR%\idor_user_%%I.status.txt" echo curl_failed
    set /a FAILURES+=1
  )
)

echo %LOG_PREFIX% IDOR evidence capture complete.
exit /b %FAILURES%
