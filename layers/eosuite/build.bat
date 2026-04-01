@echo off
cd /d "%~dp0"

REM Auto-detect GCC
where gcc >nul 2>nul && (
    set GCC=gcc
    goto :found
)
if exist tools\mingw64\bin\gcc.exe (
    set GCC=tools\mingw64\bin\gcc.exe
    goto :found
)
echo ERROR: GCC not found. Install MinGW-w64 or add gcc to PATH.
pause
exit /b 1

:found
set CFLAGS=-Os -Iinclude
set LDFLAGS=-lws2_32 -lm

echo [EoSuite Build]
echo Compiler: %GCC%
echo Compiling...

%GCC% %CFLAGS% -o EoSuite.exe ^
  src\main.c ^
  src\calculator.c ^
  src\timer_app.c ^
  src\snake.c ^
  src\notepad.c ^
  src\hex_viewer.c ^
  src\ssh_client.c ^
  src\serial_term.c ^
  src\session_manager.c ^
  src\eguard.c ^
  src\eweb.c ^
  src\ezip.c ^
  src\ecleaner.c ^
  src\evpn.c ^
  src\echat.c ^
  src\epaint.c ^
  src\eplay.c ^
  src\ebuffer.c ^
  src\econverter.c ^
  src\epdf.c ^
  src\platform_win.c ^
  %LDFLAGS%

if %ERRORLEVEL% EQU 0 (
  echo.
  echo BUILD SUCCESS!
  echo Binary: EoSuite.exe
  for %%I in (EoSuite.exe) do echo Size: %%~zI bytes
) else (
  echo.
  echo BUILD FAILED with error code %ERRORLEVEL%
)
