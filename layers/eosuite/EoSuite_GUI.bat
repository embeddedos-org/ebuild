@echo off
REM EoSuite GUI Launcher for Windows
REM Double-click to start the graphical interface
cd /d "%~dp0"

REM Try pythonw first (no console window), then python
where pythonw >nul 2>nul && (
    pythonw EoSuite_GUI.py
    goto :eof
)

where python >nul 2>nul && (
    python EoSuite_GUI.py
    goto :eof
)

echo ERROR: Python not found. Install from https://python.org
pause
