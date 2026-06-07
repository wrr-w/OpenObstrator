@echo off
chcp 65001 >nul
echo ========================================
echo OpenObstrator - Build Package
echo ========================================

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found: .venv\Scripts\python.exe
    echo Please create a virtual environment first.
    pause
    exit /b 1
)

echo [1/3] Installing build dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [2/3] Cleaning previous build...
if exist "dist" rmdir /S /Q "dist"
if exist "build" rmdir /S /Q "build"

echo.
echo [3/3] Building executable with PyInstaller...
pyinstaller --clean -y build.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo Executable: dist\OpenObstrator.exe
echo ========================================

pause
