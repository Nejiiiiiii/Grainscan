@echo off
REM ============================================================================
REM  GrainScan - one-click Windows installer builder.
REM
REM  This is the *second* stage of packaging. Run build_exe.bat first to
REM  produce dist\GrainScan\GrainScan.exe via PyInstaller; then run this
REM  script to wrap that folder into a single GrainScan-Setup-X.Y.Z.exe
REM  installer using Inno Setup.
REM
REM  Usage:
REM    build_installer.bat                          - build with defaults
REM    build_installer.bat --bundle <path>          - PyInstaller dist folder
REM                                                   (defaults to
REM                                                   F:\GrainScanBuild\dist\GrainScan)
REM    build_installer.bat --iscc   <path>          - ISCC.exe override
REM    build_installer.bat --version 1.2.3          - override AppVersion
REM
REM  Output:
REM    installer_output\GrainScan-Setup-<version>.exe
REM ============================================================================

setlocal EnableDelayedExpansion

cd /d "%~dp0"

set "BUNDLE_DIR=F:\GrainScanBuild\dist\GrainScan"
set "ISCC_EXE="
set "APP_VERSION="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--bundle"  ( set "BUNDLE_DIR=%~2" & shift & shift & goto parse_args )
if /I "%~1"=="--iscc"    ( set "ISCC_EXE=%~2"   & shift & shift & goto parse_args )
if /I "%~1"=="--version" ( set "APP_VERSION=%~2" & shift & shift & goto parse_args )
if /I "%~1"=="/?"        goto usage
if /I "%~1"=="-h"        goto usage
if /I "%~1"=="--help"    goto usage
echo Unknown argument: %~1
goto usage

:usage
echo.
echo Usage:
echo     build_installer.bat [--bundle DIR] [--iscc PATH] [--version X.Y.Z]
echo.
exit /b 1

:args_done

echo.
echo === GrainScan installer build ===
echo Project root: %CD%
echo Bundle dir  : !BUNDLE_DIR!
echo.

REM ---------------------------------------------------------------------------
REM Step 1: sanity-check the PyInstaller bundle exists.
REM ---------------------------------------------------------------------------
if not exist "!BUNDLE_DIR!\GrainScan.exe" (
    echo [ERROR] PyInstaller bundle not found at:
    echo            !BUNDLE_DIR!\GrainScan.exe
    echo.
    echo         Run build_exe.bat first to produce the bundle, or pass
    echo         --bundle DIR pointing at an existing dist\GrainScan folder.
    exit /b 1
)
echo [1/3] Found PyInstaller bundle.

REM ---------------------------------------------------------------------------
REM Step 2: locate ISCC.exe (the Inno Setup command-line compiler).
REM ---------------------------------------------------------------------------
if not defined ISCC_EXE (
    for %%P in (
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        "C:\Program Files\Inno Setup 6\ISCC.exe"
        "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
    ) do (
        if not defined ISCC_EXE if exist %%~P (
            set "ISCC_EXE=%%~P"
        )
    )
)

if not defined ISCC_EXE (
    echo.
    echo [ERROR] Inno Setup compiler ^(ISCC.exe^) not found.
    echo         Install it from https://jrsoftware.org/isdl.php or run:
    echo             winget install -e --id JRSoftware.InnoSetup
    echo         then re-run this script.
    exit /b 1
)
echo [2/3] Using compiler: !ISCC_EXE!

REM ---------------------------------------------------------------------------
REM Step 3: invoke ISCC.exe.
REM ---------------------------------------------------------------------------
if not exist installer_output mkdir installer_output

set "VERSION_FLAG="
if defined APP_VERSION set "VERSION_FLAG=/DMyAppVersion=!APP_VERSION!"

echo [3/3] Compiling GrainScan.iss ...
"!ISCC_EXE!" /Qp ^
    "/DBundleDir=!BUNDLE_DIR!" ^
    "/DSourceRoot=%CD%" ^
    !VERSION_FLAG! ^
    "GrainScan.iss"

if errorlevel 1 (
    echo.
    echo [ERROR] Inno Setup compilation failed. Scroll up for details.
    exit /b 1
)

echo.
echo ============================================================================
echo  INSTALLER BUILD SUCCEEDED
echo.
for %%F in ("installer_output\GrainScan-Setup-*.exe") do (
    echo  Installer: %%~fF
    echo  Size:      %%~zF bytes
)
echo.
echo  Distribute that single .exe to your users — double-click and follow the
echo  wizard. The application installs into %%LOCALAPPDATA%%\Programs\GrainScan
echo  by default (no admin rights required).
echo ============================================================================
echo.

endlocal
exit /b 0
