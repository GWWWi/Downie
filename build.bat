@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PY=
where py >nul 2>&1 && set PY=py
if not defined PY (
    where python >nul 2>&1 && set PY=python
)
if not defined PY (
    where python3 >nul 2>&1 && set PY=python3
)
if not defined PY (
    echo ERROR: Python not found. Install Python 3.10+ and make sure it is on PATH.
    pause
    exit /b 1
)

echo DownieWin one-click build
echo Using: %PY%
echo.
%PY% build.py
if errorlevel 1 (
    echo.
    echo [!] Build failed. See output above.
    pause
    exit /b 1
)
echo.
echo [OK] Build complete. Output: dist\DownieWin\DownieWin.exe
pause
