@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "DEFAULT_OUTPUT_ROOT=%PROJECT_ROOT%\reports\mode-comparison"

if "%~1"=="" (
  set "VULNERABLE_ROOT="
) else (
  set "VULNERABLE_ROOT=%~1"
)

if "%~2"=="" (
  set "REMEDIATED_ROOT="
) else (
  set "REMEDIATED_ROOT=%~2"
)

if "%~3"=="" (
  set "OUTPUT_ROOT=%DEFAULT_OUTPUT_ROOT%"
) else (
  set "OUTPUT_ROOT=%~3"
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%" >nul 2>&1

if defined VULNERABLE_ROOT (
  echo [lab-windows] Vulnerable report root: "%VULNERABLE_ROOT%"
) else (
  echo [lab-windows] Vulnerable report root: auto-detect from reports\
)

if defined REMEDIATED_ROOT (
  echo [lab-windows] Remediated report root: "%REMEDIATED_ROOT%"
) else (
  echo [lab-windows] Remediated report root: auto-detect from reports\
)

echo [lab-windows] Output root: "%OUTPUT_ROOT%"

set "COMPARE_ARGS=--output-root ""%OUTPUT_ROOT%"""
if defined VULNERABLE_ROOT set "COMPARE_ARGS=%COMPARE_ARGS% --vulnerable-report-root ""%VULNERABLE_ROOT%"""
if defined REMEDIATED_ROOT set "COMPARE_ARGS=%COMPARE_ARGS% --remediated-report-root ""%REMEDIATED_ROOT%"""

python "%PROJECT_ROOT%\tools\generate_mode_comparison_dashboard.py" %COMPARE_ARGS%
set "COMPARE_EXIT=%ERRORLEVEL%"
if "%COMPARE_EXIT%"=="9009" (
  py -3 "%PROJECT_ROOT%\tools\generate_mode_comparison_dashboard.py" %COMPARE_ARGS%
  set "COMPARE_EXIT=%ERRORLEVEL%"
)

if not "%COMPARE_EXIT%"=="0" (
  echo [lab-windows] Comparison dashboard generation failed.
  exit /b 1
)

echo [lab-windows] Comparison assets generated:
echo [lab-windows]   "%OUTPUT_ROOT%\COMPARISON_DASHBOARD.html"
echo [lab-windows]   "%OUTPUT_ROOT%\COMPARISON_SUMMARY.md"
echo [lab-windows]   "%OUTPUT_ROOT%\comparison.json"
exit /b 0
