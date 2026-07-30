@echo off
REM ============================================================================
REM  GrainScan - one-click build script for Windows.
REM
REM  Produces dist\GrainScan\GrainScan.exe (and supporting _internal\ folder).
REM
REM  Usage:
REM    build_exe.bat                 - build with auto-detected Python
REM    build_exe.bat --clean         - wipe build\ and dist\ first
REM    build_exe.bat --python <path> - use a specific python.exe
REM
REM  Requirements:
REM    * Python 3.9 - 3.11 installed (3.9.13 matches the original venv).
REM      Download from https://www.python.org/downloads/ if needed.
REM    * Internet access for the first run (to download PyInstaller + deps).
REM    * ~6-8 GB of free disk space for the bundled environment.
REM ============================================================================

setlocal EnableDelayedExpansion

cd /d "%~dp0"

set "VENV_DIR=.venv_build"
set "PYTHON_EXE="
set "CLEAN=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--clean" (
    set "CLEAN=1"
    shift
    goto parse_args
)
if /I "%~1"=="--python" (
    set "PYTHON_EXE=%~2"
    shift
    shift
    goto parse_args
)
if /I "%~1"=="/?" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage
echo Unknown argument: %~1
goto usage

:usage
echo.
echo Usage:
echo     build_exe.bat [--clean] [--python C:\Path\To\python.exe]
echo.
exit /b 1

:args_done

echo.
echo === GrainScan build ===
echo Project root: %CD%
echo.

REM ---------------------------------------------------------------------------
REM Step 1: locate a working Python interpreter.
REM ---------------------------------------------------------------------------
if defined PYTHON_EXE (
    if not exist "!PYTHON_EXE!" (
        echo [ERROR] --python path does not exist: !PYTHON_EXE!
        exit /b 1
    )
) else (
    echo [1/5] Locating Python 3.9-3.11 ...
    for %%V in (3.11 3.10 3.9) do (
        if not defined PYTHON_EXE (
            py -%%V --version >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                for /f "delims=" %%P in ('py -%%V -c "import sys; print(sys.executable)"') do (
                    set "PYTHON_EXE=%%P"
                )
            )
        )
    )
    if not defined PYTHON_EXE (
        where python >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do (
                set "PYTHON_EXE=%%P"
            )
        )
    )
)

if not defined PYTHON_EXE (
    echo.
    echo [ERROR] No working Python 3.9-3.11 found on PATH or via the py launcher.
    echo         Install Python from https://www.python.org/downloads/ (be sure to
    echo         tick "Add python.exe to PATH"^), then re-run this script.
    echo.
    echo         Or call this script with an explicit path:
    echo             build_exe.bat --python "C:\Python311\python.exe"
    echo.
    exit /b 1
)

echo       Using Python: !PYTHON_EXE!
"!PYTHON_EXE!" --version

REM ---------------------------------------------------------------------------
REM Step 2: optional clean.
REM ---------------------------------------------------------------------------
if "!CLEAN!"=="1" (
    echo [2/5] Cleaning previous build artefacts ...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    if exist "!VENV_DIR!" rmdir /s /q "!VENV_DIR!"
) else (
    echo [2/5] Reusing existing build folders ^(pass --clean to wipe^).
)

REM ---------------------------------------------------------------------------
REM Step 3: create / reuse build venv.
REM ---------------------------------------------------------------------------
if not exist "!VENV_DIR!\Scripts\python.exe" (
    echo [3/5] Creating fresh build venv at !VENV_DIR! ...
    "!PYTHON_EXE!" -m venv "!VENV_DIR!"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo [3/5] Reusing build venv at !VENV_DIR!.
)

set "VENV_PY=!CD!\!VENV_DIR!\Scripts\python.exe"

REM ---------------------------------------------------------------------------
REM Step 4: install dependencies + PyInstaller.
REM ---------------------------------------------------------------------------
echo [4/5] Installing runtime dependencies (this is slow on first run) ...
"!VENV_PY!" -m pip install --upgrade pip wheel setuptools
if errorlevel 1 goto pip_fail

"!VENV_PY!" -m pip install -r requirements.txt
if errorlevel 1 goto pip_fail

"!VENV_PY!" -m pip install "pyinstaller>=6.6,<7.0"
if errorlevel 1 goto pip_fail

goto pip_ok

:pip_fail
echo.
echo [ERROR] pip install failed. Check the messages above and re-run.
exit /b 1

:pip_ok

REM ---------------------------------------------------------------------------
REM Step 5: run PyInstaller.
REM ---------------------------------------------------------------------------
echo [5/5] Running PyInstaller (this is the slow step) ...
"!VENV_PY!" -m PyInstaller --noconfirm GrainScan.spec
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. Scroll up for the traceback.
    exit /b 1
)

echo.
echo ============================================================================
echo  BUILD SUCCEEDED
echo.
echo  Application folder: %CD%\dist\GrainScan
echo  Launch:             %CD%\dist\GrainScan\GrainScan.exe
echo.
echo  Distribute the entire dist\GrainScan folder (NOT just the .exe).
echo  Place additional model weights (.pt files) inside dist\GrainScan\dataset\.
echo ============================================================================
echo.

endlocal
exit /b 0
