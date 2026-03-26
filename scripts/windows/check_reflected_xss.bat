@echo off
setlocal EnableExtensions
call "%~dp0common_env.bat" "%~1"

echo %LOG_PREFIX% Capturing reflected XSS response...
> "%RAW_DIR%\reflected_xss_payload.txt" echo ^<script^>alert(1)^</script^>

curl.exe -sS -L --get "%APP_URL%/profile" ^
  --data-urlencode "bio=<script>alert(1)</script>" ^
  -D "%RAW_DIR%\reflected_xss.headers.txt" ^
  -o "%RAW_DIR%\reflected_xss.html" ^
  -w "%%{http_code}" > "%RAW_DIR%\reflected_xss.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\reflected_xss.status.txt" echo curl_failed
  exit /b 1
)

echo %LOG_PREFIX% Reflected XSS response capture complete.
exit /b 0
