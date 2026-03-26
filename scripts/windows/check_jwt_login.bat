@echo off
setlocal EnableExtensions
call "%~dp0common_env.bat" "%~1"

echo %LOG_PREFIX% Capturing JWT login response...
> "%RAW_DIR%\login_request.json" echo {"username":"alice","password":"welcome123"}

curl.exe -sS -L "%API_URL%/login" ^
  -H "Content-Type: application/json" ^
  --data-binary "@%RAW_DIR%\login_request.json" ^
  -D "%RAW_DIR%\login_response.headers.txt" ^
  -o "%RAW_DIR%\login_response.json" ^
  -w "%%{http_code}" > "%RAW_DIR%\login_response.status.txt"

if errorlevel 1 (
  > "%RAW_DIR%\login_response.status.txt" echo curl_failed
  exit /b 1
)

echo %LOG_PREFIX% JWT login capture complete.
exit /b 0
