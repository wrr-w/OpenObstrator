@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

rem NOTE: keep this file ASCII-only. Non-ASCII in a .bat gets mangled by cmd.exe
rem when the file is UTF-8 but the console codepage is GBK.

echo ========================================
echo  OpenObstrator - Build Windows Installer
echo ========================================
echo.

if /i "%~1"=="rebuild" goto :rebuild

if not exist "dist\OpenObstrator.exe" (
    echo [INFO] dist\OpenObstrator.exe not found, running PyInstaller first...
    echo.
    goto :rebuild
)
goto :find_iscc

:rebuild
echo [1/2] Building with PyInstaller...
call .venv\Scripts\activate.bat
rem IMPORTANT: do NOT `rmdir dist` here. dist\data\ is RUNTIME data
rem (config.yaml, registry.json, downloads, managed instances).
rem The repo's build.bat wipes it; this script deliberately does not.
pyinstaller --clean -y build.spec
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed.
    echo.
    pause
    exit /b 1
)
echo.

:find_iscc
set "PF86=%ProgramFiles(x86)%"
set "PF=%ProgramFiles%"
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%PF86%\Inno Setup 6\ISCC.exe" set "ISCC=%PF86%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%PF%\Inno Setup 6\ISCC.exe" set "ISCC=%PF%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo [ERROR] ISCC.exe not found. Install Inno Setup first:
    echo         winget install JRSoftware.InnoSetup
    echo.
    pause
    exit /b 1
)

echo [2/2] Compiling installer...
echo        compiler: %ISCC%
echo.

"%ISCC%" "scripts\installer.iss"
if errorlevel 1 (
    echo.
    echo [ERROR] Installer compilation failed, see ISCC output above.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build Complete
echo ========================================
echo.
for %%F in ("dist\installer\*.exe") do echo   %%~nxF  (%%~zF bytes)
echo.
echo Output: dist\installer\
echo Copy that exe to the target machine and run it. No Python needed there.
echo.
pause
