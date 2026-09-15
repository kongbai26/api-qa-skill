@echo off
cd /d "%~dp0"
set "REPORT_MODE=__REPORT_MODE__"

if defined PYTHON (
    "%PYTHON%" --version >nul 2>&1
    if not errorlevel 1 goto python_ready
    set "PYTHON="
)

set "PYTHON=__PYTHON_COMMAND__"
"%PYTHON%" --version >nul 2>&1
if not errorlevel 1 goto python_ready
set "PYTHON="

where python  >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON where python3 >nul 2>&1 && set "PYTHON=python3"
if not defined PYTHON where py      >nul 2>&1 && set "PYTHON=py"
if not defined PYTHON (
    echo ERROR: python not found.
    exit /b 1
)

:python_ready
echo Using: %PYTHON%
"%PYTHON%" --version

call :verify_report_mode
if errorlevel 1 exit /b 1

"%PYTHON%" -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir
set TEST_EXIT_CODE=%ERRORLEVEL%

if %TEST_EXIT_CODE% neq 0 echo Some tests failed, continuing to generate report...

if not exist "allure-results\*-result.json" (
    echo ERROR: no *-result.json in allure-results
    exit /b 1
)

call :verify_report_mode
if errorlevel 1 exit /b 1

if /I "%REPORT_MODE%"=="official" goto report_official
if /I "%REPORT_MODE%"=="fallback" goto report_fallback
echo ERROR: invalid report mode: %REPORT_MODE%
exit /b 1

:report_official
allure generate allure-results -o allure-report --clean
if errorlevel 1 exit /b 1
if not exist "allure-report\index.html" exit /b 1
if exist "allure-report\report.html" exit /b 1
for %%F in ("allure-report\index.html") do if %%~zF LEQ 0 exit /b 1
echo Report: allure-report\index.html
goto report_done

:report_fallback
if not exist "utils\report_generator.py" (
    echo ERROR: fallback report generator is missing.
    exit /b 1
)
"%PYTHON%" utils\report_generator.py --input allure-results --output allure-report/report.html --clean
if errorlevel 1 exit /b 1
if not exist "allure-report\report.html" exit /b 1
if exist "allure-report\index.html" exit /b 1
for %%F in ("allure-report\report.html") do if %%~zF LEQ 0 exit /b 1
echo Report: allure-report\report.html

:report_done

exit /b %TEST_EXIT_CODE%

:verify_report_mode
if /I "%REPORT_MODE%"=="official" goto verify_official
if /I "%REPORT_MODE%"=="fallback" goto verify_fallback
echo ERROR: invalid report mode: %REPORT_MODE%
exit /b 1

:verify_official
where allure >nul 2>&1
if errorlevel 1 (
    echo ERROR: report mode is official but allure is unavailable.
    exit /b 1
)
allure --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: allure is not executable.
    exit /b 1
)
exit /b 0

:verify_fallback
where allure >nul 2>&1
if errorlevel 1 exit /b 0
allure --version >nul 2>&1
if errorlevel 1 exit /b 0
echo ERROR: report mode fallback conflicts with available allure. Re-materialize the runner with official mode.
exit /b 1
