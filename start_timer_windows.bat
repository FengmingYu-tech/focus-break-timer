@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "APP_SCRIPT=%SCRIPT_DIR%focus_break_timer.py"

where py >nul 2>nul
if %errorlevel%==0 (
    start "" pyw "%APP_SCRIPT%"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%APP_SCRIPT%"
    exit /b 0
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%APP_SCRIPT%"
    exit /b 0
)

echo Python was not found. Please install Python 3 first.
pause
