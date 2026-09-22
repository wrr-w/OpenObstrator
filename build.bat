@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
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

echo [1/2] Cleaning previous build...
rem 只删构建产物，**不要动 dist\data** —— 那是运行期数据
rem （config.yaml / registry.json / downloads / 纳管实例），删了要出事。
if exist "dist\OpenObstrator.exe" del /Q "dist\OpenObstrator.exe"
if exist "dist\installer" rmdir /S /Q "dist\installer"
if exist "dist\release" rmdir /S /Q "dist\release"
if exist "build" rmdir /S /Q "build"

echo.
echo [2/2] Building executable with PyInstaller...
call .venv\Scripts\activate.bat
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
