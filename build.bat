@echo off

set DEV_DIR=F:\kouya\dev\video_library_tool
set VENV=%DEV_DIR%\.venv

echo.
echo === Video Library Tool - Build .exe ===
echo.

REM -- Check venv exists --
if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] venv not found. Please run setup_dev.bat first.
    pause
    exit /b 1
)
echo [OK] venv found: %VENV%
echo.

REM -- Install PyInstaller --
echo Installing PyInstaller...
"%VENV%\Scripts\python.exe" -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] PyInstaller install failed.
    pause
    exit /b 1
)
echo [OK] PyInstaller ready
echo.

REM -- Build --
echo Building .exe (this may take a few minutes)...
cd /d "%DEV_DIR%"
"%VENV%\Scripts\python.exe" -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name "VideoLibraryTool" ^
    --clean ^
    "%DEV_DIR%\video_lib_tool.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check errors above.
    pause
    exit /b 1
)

echo.
echo ======================================
echo  Build complete!
echo  Output: %DEV_DIR%\dist\VideoLibraryTool\
echo  Run: VideoLibraryTool.exe
echo ======================================
echo.
start explorer "%DEV_DIR%\dist\VideoLibraryTool"
pause
