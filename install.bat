@echo off
REM EoS ebuild — Windows installer
REM Makes 'ebuild' command available immediately.
REM
REM Usage:
REM   install.bat           Install ebuild CLI
REM   install.bat --check   Verify installation

setlocal

if "%1"=="--check" (
    echo Checking ebuild installation...
    where ebuild >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo [OK] ebuild found
        ebuild --version
    ) else (
        echo [FAIL] ebuild not found on PATH
    )
    exit /b
)

echo Installing ebuild...

REM Step 1: Find Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    where python3 >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python not found. Install Python 3.8+ from python.org
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
)

REM Step 2: pip install
echo Installing Python package...
%PYTHON% -m pip install -e "%~dp0" --quiet 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARN] pip install -e failed, trying without editable...
    %PYTHON% -m pip install "%~dp0" --quiet 2>nul
)
echo [OK] Python package installed

REM Step 3: Check if ebuild is already on PATH
where ebuild >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] ebuild is on PATH
    goto :verify
)

REM Step 4: Find the Scripts directory and add to PATH
for /f "delims=" %%i in ('%PYTHON% -c "import site; print(site.getusersitepackages().replace(chr(92)+chr(39)lib'+chr(92)+'site-packages', chr(92)+'Scripts'))"') do set SCRIPTS_DIR=%%i

if not exist "%SCRIPTS_DIR%\ebuild.exe" (
    for /f "delims=" %%i in ('%PYTHON% -c "import sys; import os; print(os.path.join(os.path.dirname(sys.executable), chr(39)Scripts'))"') do set SCRIPTS_DIR=%%i
)

if exist "%SCRIPTS_DIR%\ebuild.exe" (
    echo Found ebuild at: %SCRIPTS_DIR%\ebuild.exe
    echo Adding to user PATH...

    REM Add to user PATH permanently
    for /f "tokens=2*" %%A in ('reg query HKCU\Environment /v PATH 2^>nul') do set "USER_PATH=%%B"
    echo %USER_PATH% | find /i "%SCRIPTS_DIR%" >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        setx PATH "%USER_PATH%;%SCRIPTS_DIR%" >nul 2>&1
        echo [OK] Added %SCRIPTS_DIR% to user PATH
    ) else (
        echo [OK] Already in PATH
    )

    REM Also set for current session
    set "PATH=%PATH%;%SCRIPTS_DIR%"
    echo [OK] PATH updated for current session
) else (
    echo [WARN] Could not find ebuild.exe in Scripts directory
    echo        You may need to add Python Scripts to your PATH manually
)

:verify
echo.
where ebuild >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo ==========================================
    echo  ebuild installed successfully!
    echo ==========================================
    echo.
    ebuild --version
    echo.
    echo Try: ebuild --help
) else (
    echo ebuild installed but not yet on PATH.
    echo Close and reopen your terminal, then run: ebuild --version
)

endlocal
