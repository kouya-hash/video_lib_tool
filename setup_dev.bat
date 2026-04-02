@echo off

set PYTHON=C:\Users\kouya\AppData\Local\Programs\Python\Python314\python.exe
set DEV_DIR=F:\kouya\dev\video_library_tool
set VENV=%DEV_DIR%\.venv

echo.
echo === Video Library Tool - Dev Setup ===
echo Python : %PYTHON%
echo DevDir : %DEV_DIR%
echo.

REM -- Check Python exists --
if not exist "%PYTHON%" (
    echo [ERROR] Python not found: %PYTHON%
    pause
    exit /b 1
)
echo [OK] Python found
"%PYTHON%" --version
echo.

REM -- Check Python version compatibility with PySide6 --
REM Python 3.14 may not have PySide6 wheels yet.
REM Try installing; if it fails we will use Python 3.12 instead.

REM -- Create dev folder --
if not exist "%DEV_DIR%" mkdir "%DEV_DIR%"
echo [OK] Dev folder ready: %DEV_DIR%

REM -- Copy source files --
set SRC=%~dp0
if exist "%SRC%video_lib_tool.py"  copy /Y "%SRC%video_lib_tool.py"  "%DEV_DIR%\video_lib_tool.py"  > nul
if exist "%SRC%requirements.txt"   copy /Y "%SRC%requirements.txt"   "%DEV_DIR%\requirements.txt"   > nul
if exist "%SRC%build.bat"          copy /Y "%SRC%build.bat"          "%DEV_DIR%\build.bat"          > nul
echo [OK] Files copied
echo.

REM -- Try PySide6 with Python 3.14 first --
echo [1/3] Trying PySide6 with Python 3.14...
"%PYTHON%" -m pip install PySide6 --quiet 2> nul
if not errorlevel 1 (
    echo [OK] PySide6 installed with Python 3.14
    set USE_PYTHON=%PYTHON%
    goto :create_venv
)

echo [WARN] PySide6 not compatible with Python 3.14.
echo        Installing Python 3.12...
echo.

REM -- Download and install Python 3.12 --
set PY312=C:\Users\kouya\AppData\Local\Programs\Python\Python312\python.exe
if not exist "%PY312%" (
    echo [2/3] Downloading Python 3.12 installer...
    set INSTALLER=%TEMP%\python312_installer.exe
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile '%TEMP%\python312_installer.exe'"
    if errorlevel 1 (
        echo [ERROR] Download failed. Please install Python 3.12 manually from python.org
        pause
        exit /b 1
    )
    echo [2/3] Installing Python 3.12 (silent)...
    "%TEMP%\python312_installer.exe" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0
    del "%TEMP%\python312_installer.exe" > nul 2>&1
    echo [OK] Python 3.12 installed
) else (
    echo [2/3] Python 3.12 already exists: %PY312%
)

if not exist "%PY312%" (
    echo [ERROR] Python 3.12 installation failed.
    echo         Please install manually: https://www.python.org/downloads/release/python-3129/
    pause
    exit /b 1
)
set USE_PYTHON=%PY312%
echo [OK] Using Python 3.12: %USE_PYTHON%
echo.

:create_venv
REM -- Create venv --
echo [3/3] Setting up virtual environment...
if not exist "%VENV%\Scripts\python.exe" (
    "%USE_PYTHON%" -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo [OK] venv created: %VENV%
) else (
    echo [OK] venv already exists
)

REM -- Install PySide6 into venv --
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%VENV%\Scripts\python.exe" -m pip install PySide6
if errorlevel 1 (
    echo [ERROR] PySide6 install failed.
    pause
    exit /b 1
)
echo [OK] PySide6 ready
echo.

REM -- Generate run_dev.bat --
(
    echo @echo off
    echo "%VENV%\Scripts\python.exe" "%DEV_DIR%\video_lib_tool.py"
    echo if errorlevel 1 pause
) > "%DEV_DIR%\run_dev.bat"
echo [OK] Launcher created: run_dev.bat
echo.

echo ======================================
echo  Setup complete!
echo  Run the tool: double-click run_dev.bat
echo ======================================
echo.
start explorer "%DEV_DIR%"
pause
