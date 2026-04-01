@echo off
echo ================================================
echo   EoSuite - Build Standalone Installer
echo ================================================
echo.

cd /d "%~dp0"

REM Auto-detect Python
where python >nul 2>nul && (
    set PYTHON=python
    goto :found
)
where python3 >nul 2>nul && (
    set PYTHON=python3
    goto :found
)
echo ERROR: Python not found. Install from https://python.org
pause
exit /b 1

:found
echo Using: %PYTHON%

echo [1/3] Cleaning previous builds...
if exist dist rd /s /q dist
if exist build rd /s /q build

echo [2/3] Building standalone .exe with PyInstaller...
%PYTHON% -m PyInstaller EoSuite.spec --clean --noconfirm 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo [3/3] Checking output...
if exist "dist\EoSuite.exe" (
    echo.
    echo ================================================
    echo   BUILD SUCCESS!
    echo ================================================
    for %%I in ("dist\EoSuite.exe") do echo   File: dist\EoSuite.exe
    for %%I in ("dist\EoSuite.exe") do echo   Size: %%~zI bytes
    echo.
    echo   Run: dist\EoSuite.exe
    echo ================================================
) else (
    echo   ERROR: EoSuite.exe not found in dist\
)

pause
