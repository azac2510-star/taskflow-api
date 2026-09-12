@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo TaskFlow has not been installed yet.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%~dp0scripts\stop_dev.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo TaskFlow could not be stopped cleanly.
    pause
)

exit /b %EXIT_CODE%
