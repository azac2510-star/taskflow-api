@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo TaskFlow has not been installed yet. Run start_taskflow.bat first.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%~dp0scripts\verify_isolation.py" %*
if errorlevel 1 (
    echo.
    echo User isolation verification failed.
    pause
    exit /b 1
)

echo.
echo You can now explain the 404 checks in an interview.
pause
exit /b 0
