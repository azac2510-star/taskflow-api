@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo TaskFlow has not been installed yet.
    pause
    exit /b 1
)

echo Running Ruff...
"%PYTHON_EXE%" -m ruff check .
if errorlevel 1 goto :failed

echo.
echo Running pytest...
"%PYTHON_EXE%" -m pytest -q
if errorlevel 1 goto :failed

echo.
echo All checks passed.
pause
exit /b 0

:failed
echo.
echo One or more checks failed.
pause
exit /b 1
