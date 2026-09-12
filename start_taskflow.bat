@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Creating Python virtual environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv ".venv"
    ) else (
        python -m venv ".venv"
    )
    if errorlevel 1 goto :error
)

"%PYTHON_EXE%" "%~dp0scripts\run_dev.py" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo TaskFlow stopped. Exit code: %EXIT_CODE%
    pause
)

exit /b %EXIT_CODE%

:error
echo.
echo Could not create the Python virtual environment.
echo Install Python 3.11 or newer and run this file again.
pause
exit /b 1
