@echo off
chcp 65001 >nul
echo ========================================
echo OpenObstrator - Running Built Application
echo ========================================

cd /d "%~dp0dist"

if not exist "OpenObstrator.exe" (
    echo [ERROR] OpenObstrator.exe not found in dist folder.
    echo Please run build.bat first.
    pause
    exit /b 1
)

echo Starting OpenObstrator...
echo.

OpenObstrator.exe 2> error.txt
if errorlevel 1 (
    echo.
    echo Program exited with error!
    echo Error output:
    type error.txt
)

echo.
echo Press any key to exit...
pause >nul
